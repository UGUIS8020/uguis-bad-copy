from flask import Blueprint, render_template, redirect, url_for, flash
from .dynamo import db
from flask_login import current_user, login_required

# Blueprintの作成
uguu = Blueprint('uguu', __name__)

@uguu.route('/')
@login_required
def show_timeline():
    """タイムラインを表示"""
    try:
        posts = db.get_posts()
        print(f"Retrieved posts: {posts}")  # デバッグログ追加
        
        # 各投稿に対していいね状態を確認
        for post in posts:
            try:
                post['is_liked_by_user'] = db.check_if_liked(post['post_id'], current_user.id)                  # デバッグログ
            except Exception as e:                
                post['is_liked_by_user'] = False
        
        # 投稿を時系列順にソート
        if posts:
            posts = sorted(posts, key=lambda x: x.get('updated_at', x.get('created_at', '')), reverse=True)
            
        return render_template(
            'uguu/timeline.html',
            posts=posts
        )
        
    except Exception as e:
        print(f"Timeline Error: {str(e)}")
        flash('タイムラインの取得中にエラーが発生しました。', 'danger')
        return redirect(url_for('index'))

@uguu.route('/my_posts')
@login_required
def show_my_posts():
    """自分の投稿のみを表示"""
    try:
        # ユーザーの投稿を取得
        posts = db.get_user_posts(current_user.id)
        
        if posts:
            posts = sorted(posts, key=lambda x: x['updated_at'], reverse=True)
            
        return render_template(
            'uguu/timeline.html',
            posts=posts,
            show_my_posts=True
        )
        
    except Exception as e:
        print(f"My Posts Error: {e}")
        flash('投稿の取得中にエラーが発生しました。', 'danger')
        return redirect(url_for('timeline.show_timeline'))