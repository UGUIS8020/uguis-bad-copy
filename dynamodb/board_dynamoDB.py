import boto3
from datetime import datetime
import os
from dotenv import load_dotenv
from flask import Flask
from botocore.exceptions import ClientError
import uuid
from typing import Optional, Dict, Any, List
from werkzeug.security import generate_password_hash

def create_app():
    app = Flask(__name__)
    load_dotenv()

    # AWS DynamoDB リソースの設定
    app.dynamodb = boto3.resource(
        'dynamodb',
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION", "ap-northeast-1")
    )

    # ユーザーテーブル名の設定
    user_table_name = os.getenv("TABLE_NAME_USER")
    if not user_table_name:
        raise ValueError("TABLE_NAME_USER is not set.")
    app.user_table_name = user_table_name

    # 掲示板テーブル名の設定 (デフォルトを"bad-board-table"に変更)
    board_table_name = os.getenv("TABLE_NAME_BOARD", "bad-board-table")
    app.board_table_name = board_table_name

    # ユーザーテーブルの初期化
    try:
        app.user_table = app.dynamodb.Table(app.user_table_name)
        print(f"User table initialized: {app.user_table}")
    except Exception as e:
        print(f"Failed to initialize user table: {e}")
        raise

    # 掲示板テーブルの初期化
    try:
        app.board_table = app.dynamodb.Table(app.board_table_name)
        print(f"Board table initialized: {app.board_table}")
    except Exception as e:
        print(f"Failed to initialize board table: {e}")
        raise

    return app

if __name__ == "__main__":
    app = create_app()
    # ここでDynamoDBテーブルへのアクセスを試してみる（任意）
    try:
        response = app.board_table.scan()
        items = response.get('Items', [])
        print(f"Found {len(items)} item(s) in board table.")
    except ClientError as e:
        print(f"Error scanning board table: {e}")