import boto3
import os
from datetime import datetime
import uuid


class DynamoDB:
    def __init__(self):
        self.dynamodb = boto3.resource(
            'dynamodb',
            aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
            aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
            region_name=os.getenv("AWS_REGION")
        )
        self.posts_table = self.dynamodb.Table('posts')
        self.users_table = self.dynamodb.Table('bad-users')


    def get_posts(self, limit=20):
        try:
            print("Attempting to get posts...")
            
            response = self.posts_table.scan(
                FilterExpression="begins_with(PK, :pk_prefix) AND begins_with(SK, :sk_prefix)",
                ExpressionAttributeValues={
                    ':pk_prefix': 'POST#',
                    ':sk_prefix': 'METADATA#'
                }
            )
            
            posts = response.get('Items', [])
            if not posts:
                print("No posts found.")
                return []

            # 各投稿にユーザー情報を追加
            for post in posts:
                user_id = post.get('user_id')
                if user_id:
                    try:
                            # ユーザーIDのフォーマットを修正
                        user_response = self.users_table.get_item(
                            Key={
                                'user#user_id': user_id  # テーブルの設定に合わせて修正
                            }
                        )
                        user = user_response.get('Item', {})
                        post['display_name'] = user.get('display_name', '名前なし')
                        post['user_name'] = user.get('user_name', 'unknown')
                    except Exception as e:
                        print(f"Error getting user data: {str(e)}")
                        post['display_name'] = '名前なし'
                        post['user_name'] = 'unknown'

            return sorted(posts, key=lambda x: x.get('created_at', ''), reverse=True)[:limit]

        except Exception as e:
            print(f"Error getting posts: {e}")
            return []

    def create_post(self, user_id, content, image_url=None):
        """新規投稿を作成"""
        try:
            post_id = str(uuid.uuid4())
            timestamp = datetime.now().isoformat()
            
            post = {
                'PK': f"POST#{post_id}",  # パーティションキー
                'SK': f"METADATA#{post_id}",  # ソートキー
                'post_id': post_id,
                'user_id': user_id,
                'content': content,
                'image_url': image_url,
                'created_at': timestamp,
                'updated_at': timestamp
            }
            print(f"Post data: {post}")  # デバッグログ
            
            self.posts_table.put_item(Item=post)
            print("Post created successfully in DynamoDB")
            return post
            
        except Exception as e:
            print(f"DynamoDB Error: {str(e)}")
            raise

    def update_post(self, post_id, content):
        """投稿を更新"""
        try:
            timestamp = datetime.now().isoformat()
            self.posts_table.update_item(
                Key={'post_id': post_id},
                UpdateExpression='SET content = :content, updated_at = :updated_at',
                ExpressionAttributeValues={
                    ':content': content,
                    ':updated_at': timestamp
                }
            )
            return True
        except Exception as e:
            print(f"Error updating post: {e}")
            raise

    def create_posts_table(self):
        """postsテーブルが存在しない場合は作成"""
        try:
            existing_tables = self.dynamodb.meta.client.list_tables()['TableNames']
            if 'post' not in existing_tables:
                table = self.dynamodb.create_table(
                    TableName='post',
                    KeySchema=[
                        {
                            'AttributeName': 'PK',
                            'KeyType': 'HASH'
                        },
                        {
                            'AttributeName': 'SK',
                            'KeyType': 'RANGE'
                        }
                    ],
                    AttributeDefinitions=[
                        {
                            'AttributeName': 'PK',
                            'AttributeType': 'S'
                        },
                        {
                            'AttributeName': 'SK',
                            'AttributeType': 'S'
                        },
                        {
                            'AttributeName': 'GSI1PK',
                            'AttributeType': 'S'
                        },
                        {
                            'AttributeName': 'GSI1SK',
                            'AttributeType': 'S'
                        }
                    ],
                    GlobalSecondaryIndexes=[
                        {
                            'IndexName': 'GSI1',
                            'KeySchema': [
                                {'AttributeName': 'GSI1PK', 'KeyType': 'HASH'},
                                {'AttributeName': 'GSI1SK', 'KeyType': 'RANGE'}
                            ],
                            'Projection': {'ProjectionType': 'ALL'}
                        }
                    ],
                    BillingMode='PAY_PER_REQUEST'
                )
                table.meta.client.get_waiter('table_exists').wait(TableName='posts')
                print("posts table created successfully")
                return True
        except Exception as e:
            print(f"Error creating posts table: {e}")
            raise

    def like_post(self, post_id, user_id):
        """投稿にいいねを追加/削除"""
        try:
            # いいねの状態を確認
            like_key = {
                'PK': f"POST#{post_id}",
                'SK': f"LIKE#{user_id}"
            }
            
            response = self.posts_table.get_item(Key=like_key)
            
            if 'Item' in response:
                # いいねを削除
                self.posts_table.delete_item(Key=like_key)
                self.update_likes_count(post_id, -1)
                return False
            else:
                # いいねを追加
                like_data = {
                    'PK': f"POST#{post_id}",
                    'SK': f"LIKE#{user_id}",
                    'user_id': user_id,
                    'created_at': datetime.now().isoformat()
                }
                self.posts_table.put_item(Item=like_data)
                self.update_likes_count(post_id, 1)
                return True
                
        except Exception as e:
            print(f"Error in like_post: {e}")
            raise

    def update_likes_count(self, post_id, increment):
        """いいね数を更新"""
        try:
            self.posts_table.update_item(
                Key={
                    'PK': f"POST#{post_id}",
                    'SK': f"METADATA#{post_id}"
                },
                UpdateExpression='ADD likes_count :inc',
                ExpressionAttributeValues={
                    ':inc': increment
                }
            )
        except Exception as e:
            print(f"Error updating likes count: {e}")
            raise

    def get_likes_count(self, post_id):
        """投稿のいいね数を取得"""
        try:
            response = self.posts_table.query(
                KeyConditionExpression="PK = :pk AND begins_with(SK, :like)",
                ExpressionAttributeValues={
                    ':pk': f"POST#{post_id}",
                    ':like': 'LIKE#'
                }
            )
            return len(response.get('Items', []))
        except Exception as e:
            print(f"Error getting likes count: {e}")
            return 0

    def check_if_liked(self, post_id, user_id):
        """ユーザーが投稿をいいねしているか確認"""
        try:
            key = {
                'PK': f"POST#{post_id}",
                'SK': f"LIKE#{user_id}"
            }
            response = self.posts_table.get_item(Key=key)
            return 'Item' in response
        except Exception as e:
            print(f"Error checking like status: {e}")
            return False

# インスタンスを作成
db = DynamoDB()