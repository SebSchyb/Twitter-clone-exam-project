from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from flask_session import Session
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
import gspread
import requests
import json
import time
import uuid
import os
import x 
import dictionary
import io
import csv

from oauth2client.service_account import ServiceAccountCredentials

from icecream import ic
ic.configureOutput(prefix=f'----- | ', includeContext=True)

app = Flask(__name__)

# Set the maximum file size to 10 MB
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024   # 1 MB

app.config['SESSION_TYPE'] = 'filesystem'
Session(app)
 

##############################
##############################
##############################
def _____USER_____(): pass 
##############################
##############################
##############################

@app.get("/")
def view_index():

    return render_template("index.html")

##############################
@app.context_processor
def global_variables():
    return dict (
        dictionary = dictionary,
        x = x
    )


##############################
@app.route("/login", methods=["GET", "POST"])
@app.route("/login/<lan>", methods=["GET", "POST"])
@x.no_cache
def login(lan = "english"):

    if lan not in x.allowed_languages: lan = "english"
    x.default_language = lan

    if request.method == "GET":
        if session.get("user", ""): return redirect(url_for("home"))
        return render_template("login.html", lan=lan)

    if request.method == "POST":
        try:
            # Validate           
            user_email = x.validate_user_email(lan)
            user_password = x.validate_user_password(lan)
            # Connect to the database
            q = "SELECT * FROM users WHERE user_email = %s AND user_is_active = 1"
            db, cursor = x.db()
            cursor.execute(q, (user_email,))
            user = cursor.fetchone()
            if not user: 
                raise Exception(dictionary.user_not_found[lan], 400)

            if not check_password_hash(user["user_password"], user_password):
                raise Exception(dictionary.invalid_credentials[lan], 400)

            if user["user_verification_key"] != "":
                raise Exception(dictionary.user_not_verified[lan], 400)

            user.pop("user_password")

            session["user"] = user
            return f"""<browser mix-redirect="/home"></browser>"""
        

        except Exception as ex:
            ic(ex)

            # User errors😂😂😂
            if ex.args[1] == 400:
                toast_error = render_template("___toast_error.html", message=ex.args[0])
                return f"""<browser mix-update="#toast">{ toast_error }</browser>""", 400

            # System or developer error
            toast_error = render_template("___toast_error.html", message="System under maintenance")
            return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500

        finally:
            if "cursor" in locals(): cursor.close()
            if "db" in locals(): db.close()

@app.post("/api_delete_profile")
def api_delete_profile():
    try:
        user = session.get("user", "")
        if not user:
            return "error", 400

        db, cursor = x.db()
        #verify dinmor
        q = "SELECT user_pk FROM users WHERE user_pk = %s"
        cursor.execute(q, (user["user_pk"],))
        row = cursor.fetchone()

        if not row: 
            toast_error = render_template("_toast_error.html", message="ok")
            return f"""<browser mix-bottom='#toast>{toast_error}'</browser>"""
        if row["user_pk"]!=user["user_pk"]:
            toast_error = render_template("_toast_error.html", message="det kan du ikke")
            return f"""<browser mix-bottom='#toast>{toast_error}'</browser>"""
        
        q = "UPDATE users SET user_is_active = 0 WHERE user_pk = %s"
        cursor.execute(q, (user["user_pk"],))
        db.commit()

        session.clear()
        return """<browser mix-redirect="/login"></browser>"""
        
    except Exception as ex:
        ic(ex)
        toast_error = render_template("___toast_error.html", message="System under maintenance")
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.route("/signup", methods=["GET", "POST"])
@app.route("/signup/<lan>", methods=["GET", "POST"])
def signup(lan = "english"):

    if lan not in x.allowed_languages: lan = "english"
    x.default_language = lan

    if request.method == "GET":
        return render_template("signup.html", lan=lan)

    if request.method == "POST":
        try:
            # Validate
            user_email = x.validate_user_email()
            user_password = x.validate_user_password()
            user_username = x.validate_user_username()
            user_first_name = x.validate_user_first_name()

            user_pk = uuid.uuid4().hex
            user_last_name = ""
            user_avatar_path = "https://avatar.iran.liara.run/public/40"
            user_verification_key = uuid.uuid4().hex
            user_verified_at = 0

            user_hashed_password = generate_password_hash(user_password)

            # Connect to the database
            q = "INSERT INTO users VALUES(%s, %s, %s, %s, %s, %s, %s, %s, %s)"
            db, cursor = x.db()
            cursor.execute(q, (user_pk, user_email, user_hashed_password, user_username, 
            user_first_name, user_last_name, user_avatar_path, user_verification_key, user_verified_at))
            db.commit()

            # send verification email
            email_verify_account = render_template("_email_verify_account.html", user_verification_key=user_verification_key)
            ic(email_verify_account)
            x.send_email(user_email, "Verify your account", email_verify_account)

            return f"""<mixhtml mix-redirect="{ url_for('login') }"></mixhtml>""", 400
        except Exception as ex:
            ic(ex)
            # User errors
            if ex.args[1] == 400:
                toast_error = render_template("___toast_error.html", message=ex.args[0])
                return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400
            
            # Database errors
            if "Duplicate entry" and user_email in str(ex): 
                toast_error = render_template("___toast_error.html", message="Email already registered")
                return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400
            if "Duplicate entry" and user_username in str(ex): 
                toast_error = render_template("___toast_error.html", message="Username already registered")
                return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400
            
            # System or developer error
            toast_error = render_template("___toast_error.html", message="System under maintenance")
            return f"""<mixhtml mix-bottom="#toast">{ toast_error }</mixhtml>""", 500

        finally:
            if "cursor" in locals(): cursor.close()
            if "db" in locals(): db.close()

#helper function for grabbing tweets
##############################
def grab_tweets(useronly=False, target_user_pk=None):
    user = session.get("user", "")
    if not user:
        return "error"

    db, cursor = x.db()

    # ----------------------------
    # Choose SQL query based on mode
    # ----------------------------
    if not useronly:
        # GLOBAL FEED
        q = """
        SELECT 
            users.*,
            posts.*,
            COUNT(l_all.user_fk) AS like_count,
            SUM(l_all.user_fk = %s) AS liked
        FROM users
        JOIN posts 
            ON users.user_pk = posts.post_user_fk
        LEFT JOIN likes l_all
            ON posts.post_pk = l_all.post_fk
        GROUP BY posts.post_pk
        ORDER BY RAND()
        """
        params = (user["user_pk"],)

    else:
        # USER-ONLY FEED — MUST have a target user
        if not target_user_pk:
            target_user_pk = user["user_pk"]   # default to the logged in user

        q = """
        SELECT 
            users.*,
            posts.*,
            COUNT(l_all.user_fk) AS like_count,
            SUM(l_all.user_fk = %s) AS liked
        FROM posts
        JOIN users 
            ON users.user_pk = posts.post_user_fk
        LEFT JOIN likes l_all
            ON posts.post_pk = l_all.post_fk
        WHERE posts.post_user_fk = %s
        GROUP BY posts.post_pk
        ORDER BY posts.post_pk DESC
        """
        params = (user["user_pk"], target_user_pk)

    # ----------------------------
    # Execute selected query
    # ----------------------------
    cursor.execute(q, params)
    tweets = cursor.fetchall()

    # ----------------------------
    # Attach comments
    # ----------------------------
    post_pks = [t["post_pk"] for t in tweets]

    if post_pks:
        q = f"""
        SELECT 
            comments.*,
            users.user_username,
            users.user_first_name,
            users.user_last_name,
            users.user_avatar_path
        FROM comments
        JOIN users ON users.user_pk = comments.user_fk
        WHERE comments.post_fk IN ({','.join(['%s'] * len(post_pks))})
        ORDER BY comments.comment_pk ASC
        """
        cursor.execute(q, tuple(post_pks))
        comments = cursor.fetchall()

        # Group comments by post
        comments_by_post = {pk: [] for pk in post_pks}
        for c in comments:
            comments_by_post[c["post_fk"]].append(c)

        # Attach comments to each tweet
        for t in tweets:
            t["comments"] = comments_by_post.get(t["post_pk"], [])
    else:
        for t in tweets:
            t["comments"] = []

    return tweets



##############################
@app.get("/home")
@x.no_cache
def home():
    try:
        user = session.get("user", "")
        ic(user)
        if not user:
            return redirect(url_for("login"))
        db, cursor = x.db();
        tweets = grab_tweets(useronly=False)
        
        q = "SELECT * FROM trends ORDER BY RAND() LIMIT 3"
        cursor.execute(q)
        trends = cursor.fetchall()

        q = "SELECT * FROM users WHERE user_pk != %s ORDER BY RAND() LIMIT 3"
        cursor.execute(q, (user["user_pk"],))
        suggestions = cursor.fetchall()

        return render_template("home.html", tweets=tweets, trends=trends, suggestions=suggestions, user=user)
    except Exception as ex:
        ic(ex)
        return "error"
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()



##############################
@app.route("/verify-account", methods=["GET"])
def verify_account():
    try:
        user_verification_key = x.validate_uuid4_without_dashes(request.args.get("key", ""))
        user_verified_at = int(time.time())
        db, cursor = x.db()
        q = "UPDATE users SET user_verification_key = '', user_verified_at = %s WHERE user_verification_key = %s"
        cursor.execute(q, (user_verified_at, user_verification_key))
        db.commit()
        if cursor.rowcount != 1: raise Exception("Invalid key", 400)
        return redirect( url_for('login') )
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()
        # User errors
        if ex.args[1] == 400: return ex.args[0], 400    

        # System or developer error
        return "Cannot verify user"

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.get("/logout")
def logout():
    try:
        session.clear()
        return redirect(url_for("login"))
    except Exception as ex:
        ic(ex)
        return "error"
    finally:
        pass



##############################
@app.get("/home-comp")
def home_comp():
    try:

        user = session.get("user", "")
        if not user: 
            return "error"

        db, cursor = x.db()

        # 1. Get tweets
        q = """
        SELECT 
            users.*,
            posts.*,
            COUNT(l_all.user_fk) AS like_count,
            SUM(l_all.user_fk = %s) AS liked
        FROM users
        JOIN posts 
            ON users.user_pk = posts.post_user_fk
        LEFT JOIN likes l_all
            ON posts.post_pk = l_all.post_fk
        GROUP BY posts.post_pk
        ORDER BY RAND()
        LIMIT 5
        """
        cursor.execute(q, (user["user_pk"],))
        tweets = cursor.fetchall()
        
        # 2. Get all post_pks
        post_pks = [t["post_pk"] for t in tweets]
        
        if post_pks:  # Only fetch comments if we have posts
            # 3. Fetch all comments for these posts
            q = f"""
            SELECT 
                comments.*,
                users.user_username,
                users.user_first_name,
                users.user_last_name,
                users.user_avatar_path
            FROM comments
            JOIN users ON users.user_pk = comments.user_fk
            WHERE comments.post_fk IN ({','.join(['%s'] * len(post_pks))})
            ORDER BY comments.comment_pk ASC
            """
            cursor.execute(q, tuple(post_pks))
            comments = cursor.fetchall()
        
            # 4. Group comments by post_fk
            comments_by_post = {pk: [] for pk in post_pks}
            for c in comments:
                comments_by_post[c["post_fk"]].append(c)
        
            # 5. Attach each comment group to its corresponding tweet
            for t in tweets:
                t["comments"] = comments_by_post.get(t["post_pk"], [])
        else:
            # No posts → no comments
            for t in tweets:
                t["comments"] = []
        
        ic("home-comp fired")
        html = render_template("_home_comp.html", tweets=tweets, user=user, comment={})
        return f"""<mixhtml mix-update="main">{ html }</mixhtml>"""
    except Exception as ex:
        ic(ex)
        return "error"

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()



##############################
@app.get("/profile")
def profile():
    try:
        session_user = session.get("user", "")
        if not session_user:
            return redirect(url_for("login"))

        db, cursor = x.db()

        q_user = "SELECT * FROM users WHERE user_pk = %s"
        cursor.execute(q_user, (session_user["user_pk"],))
        user = cursor.fetchone()
        if not user:
            return "error"

        # q_posts = """
        #     SELECT *
        #     FROM posts
        #     JOIN users ON user_pk = post_user_fk
        #     WHERE post_user_fk = %s
        #     ORDER BY post_pk DESC
        # """
        # cursor.execute(q_posts, (user["user_pk"],))
        # tweets = cursor.fetchall()
        tweets = grab_tweets(useronly=True, target_user_pk=session_user["user_pk"])

        profile_html = render_template("_profile.html", user=user, tweets=tweets)

        return f"""<browser mix-update="main">{ profile_html }</browser>"""

    except Exception as ex:
        ic(ex)
        return "error"
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.post("/toggle_follow")
def toggle():
    try:
        user = session.get("user", "")
        if not user:
            return "error"
        data = request.get_json() or {}
        user_pk = data.get("user_pk")
        if not user_pk:
            return jsonify({"error": "missing_user_pk"}), 400
        db, cursor = x.db()
        # check if the user is already following
        q = "SELECT COUNT(*) AS cnt FROM follows WHERE user_fk = %s AND follower_fk = %s"
        cursor.execute(q, (user_pk, user["user_pk"]))
        already = cursor.fetchone()["cnt"] > 0

        if already:
            # unfollow (delete)
            q = "DELETE FROM follows WHERE user_fk = %s AND follower_fk = %s"
            cursor.execute(q, (user_pk, user["user_pk"]))
            db.commit()
            followed = False
        else:
            # follow (insert)
            q = "INSERT INTO follows (user_fk, follower_fk) VALUES (%s, %s)"
            try:
                cursor.execute(q, (user_pk, user["user_pk"]))
                db.commit()
            except Exception as e:
                # handle race/duplicate gracefully
                db.rollback()
            followed = True

        # get updated follower count
        q = "SELECT COUNT(*) AS cnt FROM follows WHERE user_fk = %s"
        cursor.execute(q, (user_pk,))
        follower_count = cursor.fetchone()["cnt"]

        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

        return jsonify({"followed": followed, "follower_count": follower_count})
    except Exception as ex:
        ic(ex)
        return "Error"
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()





##############################
@app.post("/toggle_like")
def toggle_like():
    try:
        user = session.get("user", "")
        if not user:
            return jsonify({"error": "not_logged_in"}), 401

        data = request.get_json() or {}
        post_pk = data.get("post_pk")
        if not post_pk:
            return jsonify({"error": "missing_post_pk"}), 400

        db, cursor = x.db()

        # check if the user already liked the post
        q = "SELECT COUNT(*) AS cnt FROM likes WHERE post_fk = %s AND user_fk = %s"
        cursor.execute(q, (post_pk, user["user_pk"]))
        already = cursor.fetchone()["cnt"] > 0

        if already:
            # unlike (delete)
            q = "DELETE FROM likes WHERE post_fk = %s AND user_fk = %s"
            cursor.execute(q, (post_pk, user["user_pk"]))
            db.commit()
            liked = False
        else:
            # like (insert)
            q = "INSERT INTO likes (post_fk, user_fk) VALUES (%s, %s)"
            try:
                cursor.execute(q, (post_pk, user["user_pk"]))
                db.commit()
            except Exception as e:
                # handle race/duplicate gracefully
                ic(e)
                db.rollback()
            liked = True

        # get updated like count
        q = "SELECT COUNT(*) AS cnt FROM likes WHERE post_fk = %s"
        cursor.execute(q, (post_pk,))
        like_count = cursor.fetchone()["cnt"]

        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

        return jsonify({"followed": liked, "like_count": like_count})
    except Exception as ex:
        ic(ex)
        try:
            if "db" in locals(): db.rollback()
        except:
            pass
        return jsonify({"error": "server_error"}), 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()




##############################
@app.patch("/api-edit-post/<post_pk>")
def api_edit_post(post_pk):
    try:
        # User must be logged in
        user = session.get("user", "")
        if not user:
            toast_error = render_template("___toast_error.html", message="You must be logged in")
            return f"""<browser mix-bottom="#toast">{toast_error}</browser>"""

        # User must not be blocked
        if user["user_is_blocked"] == 1:
            toast_error = render_template("___toast_error.html", message="Your account is blocked - please check your email")
            return f"""<browser mix-bottom="#toast">{toast_error}</browser>"""
        
        # FormData input (NOT JSON)
        message = request.form.get("message", "").strip()

        # Validate message length
        if not (1 <= len(message) <= x.POST_MAX_LEN):
            toast_error = render_template("___toast_error.html", message="Invalid post length")
            return f"""<browser mix-bottom="#toast">{toast_error}</browser>"""

        # DB connection
        db, cursor = x.db()

        # Ownership check
        q = "SELECT post_user_fk FROM posts WHERE post_pk = %s"
        cursor.execute(q, (post_pk,))
        row = cursor.fetchone()

        if not row:
            toast_error = render_template("___toast_error.html", message="Post not found")
            return f"""<browser mix-bottom="#toast">{toast_error}</browser>"""

        if row["post_user_fk"] != user["user_pk"]:
            toast_error = render_template("___toast_error.html", message="You cannot edit this post")
            return f"""<browser mix-bottom="#toast">{toast_error}</browser>"""

        # Update post
        q = "UPDATE posts SET post_message = %s WHERE post_pk = %s"
        cursor.execute(q, (message, post_pk))
        db.commit()

        # Toast + re-render post container
        toast_ok = render_template("___toast_ok.html", message="Post updated")
        html_post_container = render_template("___post_container.html")

        return f"""
            <browser mix-replace="#text-{post_pk}">{message}</browser>
            <browser mix-bottom="#toast">{toast_ok}</browser>
            <browser mix-replace="#post_container">{html_post_container}</browser>
        """

    except Exception as ex:
        ic(ex)
        if "db" in locals():
            db.rollback()
        toast_error = render_template("___toast_error.html", message="System under maintenance")
        return f"""<browser mix-bottom="#toast">{toast_error}</browser>""", 500

    finally:
        if "cursor" in locals():
            cursor.close()
        if "db" in locals():
            db.close()



##############################
@app.delete("/api-delete-post/<post_pk>")
def api_delete_post(post_pk):
    try:
        user = session.get("user", "")
        if not user:
            toast_error = render_template("___toast_error.html", message="You must be logged in")
            return f"""<browser mix-bottom="#toast">{toast_error}</browser>"""

        db, cursor = x.db()

        # Verify ownership
        q = "SELECT post_user_fk FROM posts WHERE post_pk = %s"
        cursor.execute(q, (post_pk,))
        row = cursor.fetchone()

        if not row:
            toast_error = render_template("___toast_error.html", message="Post not found")
            return f"""<browser mix-bottom="#toast">{toast_error}</browser>"""

        if row["post_user_fk"] != user["user_pk"]:
            toast_error = render_template("___toast_error.html", message="You cannot delete this post")
            return f"""<browser mix-bottom="#toast">{toast_error}</browser>"""

        # Delete post
        q = "DELETE FROM posts WHERE post_pk = %s"
        cursor.execute(q, (post_pk,))
        db.commit()

        toast_ok = render_template("___toast_ok.html", message="Post deleted")
        html_post_container = render_template("___post_container.html")
        return f"""
            <browser mix-remove="#tweet-{post_pk}"></browser>
            <browser mix-bottom="#toast">{toast_ok}</browser>
            <browser mix-replace="#post_container">{html_post_container}</browser>
        """

    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()

        toast_error = render_template("___toast_error.html", message="System under maintenance")
        return f"""<browser mix-bottom="#toast">{toast_error}</browser>""", 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()



##############################
@app.route("/api-create-post", methods=["POST"])
def api_create_post():
    try:
        user = session.get("user", "")   
        if not user: return "invalid user"
                # User must not be blocked
        if user["user_is_blocked"] == 1:
            toast_error = render_template("___toast_error.html", message="Your account is blocked - please check your email")
            return f"""<browser mix-bottom="#toast">{toast_error}</browser>"""
        user_pk = user["user_pk"]   
        post = x.validate_post(request.form.get("post", ""))
        post_pk = uuid.uuid4().hex
        post_image_path = ""
        db, cursor = x.db()
        q = "INSERT INTO posts VALUES(%s, %s, %s, %s, %s)"
        cursor.execute(q, (post_pk, user_pk, post, 0, post_image_path))
        db.commit()
        toast_ok = render_template("___toast_ok.html", message="The world is reading your post!")
        tweet = {
            "post_pk": post_pk,
            "user_pk": user_pk,
            "post_user_fk": user_pk,
            "user_first_name": user["user_first_name"],
            "user_last_name": user["user_last_name"],
            "user_username": user["user_username"],
            "user_avatar_path": user["user_avatar_path"],
            "post_message": post,
            "liked": None,
        }
        html_post_container = render_template("___post_container.html")
        html_post = render_template("_tweet.html", tweet=tweet, user=user)
        return f"""
            <browser mix-bottom="#toast">{toast_ok}</browser>
            <browser mix-top="#posts">{html_post}</browser>
            <browser mix-replace="#post_container">{html_post_container}</browser>
        """
    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()

        # User errors
        if "x-error post" in str(ex):
            toast_error = render_template("___toast_error.html", message=f"Post - {x.POST_MIN_LEN} to {x.POST_MAX_LEN} characters")
            return f"""<browser mix-bottom="#toast">{toast_error}</browser>"""

        # System or developer error
        toast_error = render_template("___toast_error.html", message="System under maintenance")
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()    

##############################
@app.post("/api-create-comment/<post_pk>")
def api_create_comment(post_pk):
    try:
        user = session.get("user", "")   
        if not user: return "invalid user"
        db, cursor = x.db()
        user_pk = user["user_pk"]  
        comment_pk = uuid.uuid4().hex
        comment = x.validate_post(request.form.get("comment", "").strip())
        q = "INSERT INTO comments VALUES(%s, %s, %s, %s)"
        cursor.execute(q, (comment_pk, user_pk, post_pk, comment))
        db.commit()
        ic(comment)
        finalcomment = {
            "user_username": user["user_username"],
            "user_first_name": user["user_first_name"],
            "user_last_name": user["user_last_name"],
            "comment_content": comment,
            "comment_pk": comment_pk
        }
        toast_ok = render_template("___toast_ok.html", message="The world is reading your comment!")
        html_comment = render_template("__comment.html", comment=finalcomment)
        return f"""
        <browser mix-bottom="#toast">{ toast_ok }</browser>
        <browser mix-top="#comments-{post_pk}">{html_comment}</browser>
        """
    except Exception as ex:
        if "x-error post" in str(ex):
            toast_error = render_template("___toast_error.html", message=f"Comment - {x.POST_MIN_LEN} to {x.POST_MAX_LEN} characters")
            return f"""<browser mix-bottom="#toast">{toast_error}</browser>"""

        # System or developer error
        ic(ex)
        toast_error = render_template("___toast_error.html", message="System under maintenance")
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()    



##############################
@app.route("/api-update-profile", methods=["POST"])
def api_update_profile():
    try:
        user = session.get("user", "")
        if not user: return "invalid user"

        user_email = x.validate_user_email()
        user_username = x.validate_user_username()
        user_first_name = x.validate_user_first_name()
        user_bio = request.form.get("user_bio", "").strip()
        user_avatar_path = request.form.get("user_avatar_path", "").strip()

        db, cursor = x.db()
        q = """
            UPDATE users
            SET user_email = %s,
                user_username = %s,
                user_first_name = %s,
                user_bio = %s,
                user_avatar_path = %s
            WHERE user_pk = %s
        """
        cursor.execute(q, (
            user_email,
            user_username,
            user_first_name,
            user_bio,
            user_avatar_path,
            user["user_pk"]
        ))
        db.commit()

        toast_ok = render_template("___toast_ok.html", message="Profile updated successfully")
        return f"""
            <browser mix-bottom="#toast">{toast_ok}</browser>
            <browser mix-update="#profile_tag .name">{user_first_name}</browser>
            <browser mix-update="#profile_tag .handle">@{user_username}</browser>
            <browser mix-update="#profile_bio">{user_bio}</browser>
        """, 200
    
    except Exception as ex:
        ic(ex)
        # User errors
        if ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400
        
        # Database errors
        if "Duplicate entry" and user_email in str(ex): 
            toast_error = render_template("___toast_error.html", message="Email already registered")
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400
        if "Duplicate entry" and user_username in str(ex): 
            toast_error = render_template("___toast_error.html", message="Username already registered")
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400
        
        # System or developer error
        toast_error = render_template("___toast_error.html", message="System under maintenance")
        return f"""<mixhtml mix-bottom="#toast">{ toast_error }</mixhtml>""", 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()



##############################
@app.post("/api-search")
def api_search():
    try:
        # TODO: The input search_for must be validated
        search_for = request.form.get("search_for", "")
        if not search_for: return """empty search field""", 400
        part_of_query = f"%{search_for}%"
        ic(search_for)
        db, cursor = x.db()
        q = "SELECT * FROM users WHERE user_username LIKE %s"
        cursor.execute(q, (part_of_query,))
        users = cursor.fetchall()
        return jsonify(users)
    except Exception as ex:
        ic(ex)
        return str(ex)
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

@app.get("/test-admin-route")
def test_admin_route():
    try:
        user = session.get("user", "")
        if not user:
            return "No user found"
        if not user["user_is_admin"] == 1:
            return "Not allowed for non-admin users."
        return "Success"
    except Exception as ex:
        ic(ex)

##############################
@app.patch("/admin-block-post")
def admin_block_post():
    try:
        user = session.get("user", "")
        if not user:
            return "No user found"
        if not user["user_is_admin"] == 1:
            return "Not allowed for non-admin users.", 400
        post_pk = request.form.get("block-input", "").strip()
        ic(post_pk)
        db, cursor = x.db()
        # Grap post and check if deleted
        q = "SELECT * FROM posts WHERE post_pk = %s"
        cursor.execute(q, (post_pk,))
        post = cursor.fetchone()
        if not post:
            toast_error = render_template("___toast_error.html", message="Post does not exist")
            return f"""<browser mix-bottom="#toast">{toast_error}</browser>"""
        
        # Check if post is already blocked
        q = "SELECT * FROM posts WHERE post_pk = %s AND post_is_blocked = 1"
        cursor.execute(q, (post_pk,))
        post = cursor.fetchone()
        if post:
            toast_error = render_template("___toast_error.html", message="Post is already blocked")
            return f"""<browser mix-bottom="#toast">{toast_error}</browser>"""
        
        # Update record in db
        q = "UPDATE posts SET post_is_blocked = 1 WHERE post_pk = %s"
        cursor.execute(q, (post_pk,))
        db.commit()
        # Send email to user
        q = """
        SELECT users.user_email
        FROM users
        JOIN posts ON users.user_pk = posts.post_user_fk
        WHERE posts.post_pk = %s
        """
        cursor.execute(q, (post_pk,))
        email = cursor.fetchone()
        user_email = email["user_email"]
        email_html = f'Your post has been blocked because an admin thought it to be inappropriate'
        x.send_email(user_email, "Note from admin", email_html)
        toast_ok = render_template("___toast_ok.html", message="Post is now blocked")
        return f"""<browser mix-bottom="#toast">{toast_ok}</browser>"""
        
    except Exception as ex:
        ic(ex)
        toast_error = render_template("___toast_error.html", message="System Error")
        return f"""<browser mix-bottom="#toast">{toast_error}</browser>"""
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.patch("/admin-block-user")
def admin_block_user():
    try:
        user = session.get("user", "")
        if not user:
            return "No user found"

        # Must be admin
        if user.get("user_is_admin") != 1:
            return "Not allowed for non-admin users.", 400

        target_user_pk = request.form.get("block-user-input", "").strip()
        ic(target_user_pk)

        db, cursor = x.db()

        # 1. Does the user exist?
        q = "SELECT * FROM users WHERE user_pk = %s"
        cursor.execute(q, (target_user_pk,))
        target_user = cursor.fetchone()

        if not target_user:
            toast_error = render_template("___toast_error.html",
                                          message="User does not exist")
            return f"""<browser mix-bottom="#toast">{toast_error}</browser>"""

        # 2. Is the user already blocked?
        if target_user["user_is_blocked"] == 1:
            toast_error = render_template("___toast_error.html",
                                          message="User is already blocked")
            return f"""<browser mix-bottom="#toast">{toast_error}</browser>"""

        # 3. Block the user
        q = "UPDATE users SET user_is_blocked = 1 WHERE user_pk = %s"
        cursor.execute(q, (target_user_pk,))
        db.commit()

        # 4. Email the user
        user_email = target_user["user_email"]
        email_html = (
            "Your account has been blocked by an administrator due to a "
            "violation of our community guidelines."
        )

        x.send_email(user_email, "Account Blocked", email_html)

        # 5. Toast
        toast_ok = render_template("___toast_ok.html",
                                   message="User is now blocked")
        return f"""<browser mix-bottom="#toast">{toast_ok}</browser>"""

    except Exception as ex:
        ic(ex)
        toast_error = render_template("___toast_error.html",
                                      message="System Error")
        return f"""<browser mix-bottom="#toast">{toast_error}</browser>"""

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################
@app.get("/get-data-from-sheet")
def get_data_from_sheet():
    try:
        user = session.get("user", "")
        if not user:
            return "No user found"
        if not user["user_is_admin"] == 1:
            return "Not allowed for non-admin users."
        # Check if the admin is running this end-point, else show error

        # flaskwebmail
        # Create a google sheet
        # share and make it visible to "anyone with the link"
        # In the link, find the ID of the sheet. Here: 1aPqzumjNp0BwvKuYPBZwel88UO-OC_c9AEMFVsCw1qU
        # Replace the ID in the 2 places bellow
        url= f"https://docs.google.com/spreadsheets/d/{x.google_spread_sheet_key}/export?format=csv&id={x.google_spread_sheet_key}"
        res=requests.get(url=url)
        # ic(res.text) # contains the csv text structure
        csv_text = res.content.decode('utf-8')
        csv_file = io.StringIO(csv_text) # Use StringIO to treat the string as a file
        
        # Initialize an empty list to store the data
        data = {}

        # Read the CSV data
        reader = csv.DictReader(csv_file)
        ic(reader)
        # Convert each row into the desired structure
        for row in reader:
            item = {
                    'english': row['english'],
                    'danish': row['danish'],
                    'spanish': row['spanish']
                
            }
            # Append the dictionary to the list
            data[row['key']] = (item)

        # Convert the data to JSON
        json_data = json.dumps(data, ensure_ascii=False, indent=4) 
        # ic(data)

        # Save data to the file
        with open("dictionary.json", 'w', encoding='utf-8') as f:
            f.write(json_data)

        return "ok"
    except Exception as ex:
        ic(ex)
        return str(ex)
    finally:
        pass

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    if request.method == "GET":
        return render_template("_forgot_password.html")

    if request.method == "POST":
        try:
            user_email = x.validate_user_email()

            db, cursor = x.db()
            cursor.execute("SELECT * FROM users WHERE user_email=%s", (user_email,))
            user = cursor.fetchone()
            if not user:
                raise Exception("Email not found", 400)

            reset_key = uuid.uuid4().hex

            cursor.execute("UPDATE users SET user_reset_key=%s WHERE user_pk=%s",
                           (reset_key, user["user_pk"]))
            db.commit()

            reset_url = f"http://127.0.0.1/reset-password/{reset_key}"
            email_html = f'To reset your password, click here: <a href="{reset_url}">Reset password</a>'
            x.send_email(user_email, "Reset your password", email_html)


            return f"<browser mix-update='#toast'>Password reset email sent.</browser>"

        except Exception as ex:
            toast = render_template("___toast_error.html", message=ex.args[0])
            return f"<browser mix-update='#toast'>{toast}</browser>", 400
        
        finally:
            if "cursor" in locals(): cursor.close()
            if "db" in locals(): db.close()
##########

@app.route("/reset-password/<reset_key>", methods=["GET", "POST"])
def reset_password(reset_key):

    if request.method == "GET":
        return render_template("_reset_password.html", reset_key=reset_key)

    if request.method == "POST":
        try:
            new_password = x.validate_user_password()

            db, cursor = x.db()
            cursor.execute("SELECT * FROM users WHERE user_reset_key=%s", (reset_key,))
            user = cursor.fetchone()
            if not user:
                raise Exception("Invalid reset link", 400)

            hashed = generate_password_hash(new_password)

            cursor.execute("""UPDATE users SET user_password=%s, user_reset_key='' WHERE user_pk=%s""", (hashed, user["user_pk"]))
            db.commit()

            return render_template("_password_reset_succes.html")


        except Exception as ex:
            toast = render_template("___toast_error.html", message=ex.args[0])
            return f"<browser mix-bottom='#toast'>{toast}</browser>", 400

        finally:
            if "cursor" in locals(): cursor.close()
            if "db" in locals(): db.close()
