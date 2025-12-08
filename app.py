from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from flask_session import Session
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from werkzeug.exceptions import RequestEntityTooLarge

import requests
import json
import time
import uuid
import os
import x 
import dictionary
import io
import csv
from pathlib import Path
from flask import current_app
BASE_DIR = Path(__file__).resolve().parent
from icecream import ic
ic.configureOutput(prefix=f'----- | ', includeContext=True)
#Disable IC if in production
if "PYTHONANYWHERE_DOMAIN" in os.environ:
    ic.disable()
    domain = "https://smolly.eu.pythonanywhere.com"
else: 
    domain = "http://127.0.0.1"

app = Flask(__name__)

app.config['UPLOAD_FOLDER'] = Path(app.root_path) / 'static' / 'images'
app.config['UPLOAD_EXTENSIONS'] = ['.jpg', '.jpeg', '.png', '.gif']
app.config['MAX_CONTENT_LENGTH'] = 4 * 1024 * 1024  # 4 mb
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
            user_email = x.validate_user_email(lan)
            user_password = x.validate_user_password(lan)
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
            user["user_language"] = lan
            session["user"] = user
            return f"""<browser mix-redirect="/home"></browser>"""
        

        except Exception as ex:
            ic(ex)

            if ex.args[1] == 400:
                toast_error = render_template("___toast_error.html", message=ex.args[0])
                return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 400
            
            toast_error = render_template("___toast_error.html", message=x.lans("system_under_maintenance"))
            return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500

        finally:
            if "cursor" in locals(): cursor.close()
            if "db" in locals(): db.close()

@app.post("/api-delete-profile")
def api_delete_profile():
    try:
        user = session.get("user", "")
        if not user:
            return "error not user", 400

        db, cursor = x.db()
        q = "SELECT user_pk FROM users WHERE user_pk = %s"
        cursor.execute(q, (user["user_pk"],))
        row = cursor.fetchone()

        if not row: 
            toast_error = render_template("_toast_error.html", message=x.lans("ok"))
            return f"""<browser mix-bottom='#toast>{toast_error}'</browser>"""
        if row["user_pk"]!=user["user_pk"]:
            toast_error = render_template("_toast_error.html", message=x.lans("you_can't_do_that"))
            return f"""<browser mix-bottom='#toast>{toast_error}'</browser>"""
        
        q = "UPDATE users SET user_is_active = 0 WHERE user_pk = %s"
        cursor.execute(q, (user["user_pk"],))
        db.commit()

        session.clear()
        return """<browser mix-redirect="/login"></browser>"""
        
    except Exception as ex:
        ic(ex)
        toast_error = render_template("___toast_error.html", message=x.lans("system_under_maintenance"))
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

            q = """INSERT INTO users (
                user_pk,
                user_email,
                user_password,
                user_username,
                user_first_name,
                user_last_name,
                user_avatar_path,
                user_verification_key,
                user_verified_at
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """
            db, cursor = x.db()
            cursor.execute(q, (user_pk, user_email, user_hashed_password, user_username, 
            user_first_name, user_last_name, user_avatar_path, user_verification_key, user_verified_at))
            db.commit()

            # send verification email
            email_verify_account = render_template("_email_verify_account.html", user_verification_key=user_verification_key, domain=domain)
            ic(email_verify_account)
            x.send_email(user_email, "Verify your account", email_verify_account)

            return f"""<mixhtml mix-redirect="{ url_for('login') }"></mixhtml>""", 400
        except Exception as ex:
            ic(ex)
            if ex.args[1] == 400:
                toast_error = render_template("___toast_error.html", message=ex.args[0])
                return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400
            
            if "Duplicate entry" and user_email in str(ex): 
                toast_error = render_template("___toast_error.html", message=x.lans("email_already_registered")) 
                return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400
            if "Duplicate entry" and user_username in str(ex): 
                toast_error = render_template("___toast_error.html", message=x.lans("username_already_registered"))
                return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400
            
            toast_error = render_template("___toast_error.html", message=x.lans("system_under_maintenance"))
            return f"""<mixhtml mix-bottom="#toast">{ toast_error }</mixhtml>""", 500

        finally:
            if "cursor" in locals(): cursor.close()
            if "db" in locals(): db.close()

#helper function for grabbing tweets
##############################
def grab_tweets(useronly=False, target_user_pk=None, blockedonly=False):
    user = session.get("user", "")
    if not user:
        return "error"

    db, cursor = x.db()
    if blockedonly:
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
        WHERE posts.post_is_blocked = 1
        GROUP BY posts.post_pk
        ORDER BY posts.post_pk DESC
        """
        params = (user["user_pk"],)

    elif not useronly:
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
        WHERE posts.post_is_blocked = 0
        GROUP BY posts.post_pk
        ORDER BY posts.post_pk DESC
        """
        params = (user["user_pk"],)

    elif useronly:
        if not target_user_pk:
            target_user_pk = user["user_pk"]

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

    ic(q)
    cursor.execute(q, params)
    tweets = cursor.fetchall()

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

        comments_by_post = {pk: [] for pk in post_pks}
        for c in comments:
            comments_by_post[c["post_fk"]].append(c)

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
        db, cursor = x.db()
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
        if ex.args[1] == 400: return ex.args[0], 400    

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

        tweets = grab_tweets(useronly=False)

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

        q = "SELECT * FROM users WHERE user_pk = %s"
        cursor.execute(q, (session_user["user_pk"],))
        user = cursor.fetchone()
        if not user:
            return "error"

        tweets = grab_tweets(useronly=True, target_user_pk=session_user["user_pk"])

        profile_html = render_template("_profile.html", user=user, tweets=tweets, is_me=True)

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
        q = "SELECT COUNT(*) AS cnt FROM follows WHERE user_fk = %s AND follower_fk = %s"
        cursor.execute(q, (user_pk, user["user_pk"]))
        already = cursor.fetchone()["cnt"] > 0

        if already:
            q = "DELETE FROM follows WHERE user_fk = %s AND follower_fk = %s"
            cursor.execute(q, (user_pk, user["user_pk"]))
            db.commit()
            followed = False
        else:
            q = "INSERT INTO follows (user_fk, follower_fk) VALUES (%s, %s)"
            try:
                cursor.execute(q, (user_pk, user["user_pk"]))
                db.commit()
            except Exception as e:
                db.rollback()
            followed = True

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

        q = "SELECT COUNT(*) AS cnt FROM likes WHERE post_fk = %s AND user_fk = %s"
        cursor.execute(q, (post_pk, user["user_pk"]))
        already = cursor.fetchone()["cnt"] > 0

        if already:
            q = "DELETE FROM likes WHERE post_fk = %s AND user_fk = %s"
            cursor.execute(q, (post_pk, user["user_pk"]))
            db.commit()
            liked = False
        else:
            q = "INSERT INTO likes (post_fk, user_fk) VALUES (%s, %s)"
            try:
                cursor.execute(q, (post_pk, user["user_pk"]))
                db.commit()
            except Exception as e:
                ic(e)
                db.rollback()
            liked = True

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
        user = session.get("user", "")
        if not user:
            toast_error = render_template("___toast_error.html", message=x.lans("you_must_be_logged_in"))
            return f"""<browser mix-bottom="#toast">{toast_error}</browser>"""

        if user["user_is_blocked"] == 1:
            toast_error = render_template("___toast_error.html", message=x.lans("your_account_is_blocked_please_check_your_email"))
            return f"""<browser mix-bottom="#toast">{toast_error}</browser>"""
        
        message = request.form.get("message", "").strip()

        if not (1 <= len(message) <= x.POST_MAX_LEN):
            toast_error = render_template("___toast_error.html", message=x.lans("invalid_post_length"))
            return f"""<browser mix-bottom="#toast">{toast_error}</browser>"""

        db, cursor = x.db()

        q = "SELECT post_user_fk FROM posts WHERE post_pk = %s"
        cursor.execute(q, (post_pk,))
        row = cursor.fetchone()

        if not row:
            toast_error = render_template("___toast_error.html", message=x.lans("post_not_found"))
            return f"""<browser mix-bottom="#toast">{toast_error}</browser>"""

        if row["post_user_fk"] != user["user_pk"]:
            toast_error = render_template("___toast_error.html", message=x.lans("you_cannot_edit_this_post"))
            return f"""<browser mix-bottom="#toast">{toast_error}</browser>"""

        q = "UPDATE posts SET post_message = %s WHERE post_pk = %s"
        cursor.execute(q, (message, post_pk))
        db.commit()

        toast_ok = render_template("___toast_ok.html", message=x.lans("post_updated"))
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
        toast_error = render_template("___toast_error.html", message=x.lans("system_under_maintenance"))
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
        ic(post_pk)

        if not post_pk:
            return "Missing post ID", 400
        
        if not user:
            toast_error = render_template("___toast_error.html", message=x.lans("you_must_be_logged_in"))
            return f"""<browser mix-bottom="#toast">{toast_error}</browser>"""

        db, cursor = x.db()

        q = "SELECT post_user_fk FROM posts WHERE post_pk = %s"
        cursor.execute(q, (post_pk,))
        row = cursor.fetchone()

        if not row:
            toast_error = render_template("___toast_error.html", message=x.lans("post_not_found"))
            return f"""<browser mix-bottom="#toast">{toast_error}</browser>"""

        if row["post_user_fk"] != user["user_pk"]:
            toast_error = render_template("___toast_error.html", message=x.lans("you_cannot_delete_this_post"))
            return f"""<browser mix-bottom="#toast">{toast_error}</browser>"""

        q = "DELETE FROM posts WHERE post_pk = %s"
        cursor.execute(q, (post_pk,))
        db.commit()

        toast_ok = render_template("___toast_ok.html", message=x.lans("post_deleted"))
        html_post_container = render_template("___post_container.html")
        return f"""
            <browser mix-remove="#tweet-{post_pk}"></browser>
            <browser mix-remove="#comment-form-{post_pk}"></browser>
            <browser mix-remove="#comments-{post_pk}"></browser>
            <browser mix-bottom="#toast">{toast_ok}</browser>
            <browser mix-replace="#post_container">{html_post_container}</browser>
        """

    except Exception as ex:
        ic(ex)
        if "db" in locals(): db.rollback()

        toast_error = render_template("___toast_error.html", message=x.lans("system_under_maintenance"))
        return f"""<browser mix-bottom="#toast">{toast_error}</browser>""", 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.route("/api-create-post", methods=["POST"])
def api_create_post():
    try:
        user = session.get("user", "")  
        ic(user) 
        if not user: return "invalid user"

        db, cursor = x.db()
        cursor.execute("SELECT * FROM users WHERE user_pk=%s", (user["user_pk"],))
        current_user = cursor.fetchone()
        ic(current_user)
        if current_user["user_is_blocked"] == 1:
            toast_error = render_template("___toast_error.html", message=x.lans("your_account_is_blocked_please_check_your_email"))
            return f"""<browser mix-bottom="#toast">{toast_error}</browser>"""
        user_pk = user["user_pk"]   
        post = x.validate_post(request.form.get("post", ""))
        post_pk = uuid.uuid4().hex
        post_image_path = ""
        db, cursor = x.db()
        q = "INSERT INTO posts VALUES(%s, %s, %s, %s, %s, %s)"
        cursor.execute(q, (post_pk, user_pk, post, 0, post_image_path, 0))
        db.commit()
        toast_ok = render_template("___toast_ok.html", message=x.lans("the_world_is_reading_your_post"))
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

        if "x-error post" in str(ex):
            toast_error = render_template("___toast_error.html", message=x.lans("invalid_post_length"))
            return f"""<browser mix-bottom="#toast">{toast_error}</browser>"""

        toast_error = render_template("___toast_error.html", message=x.lans("system_under_maintenance"))
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
        toast_ok = render_template("___toast_ok.html", message=x.lans("the_world_is_reading_your_comment"))
        html_comment = render_template("__comment.html", comment=finalcomment)
        return f"""
        <browser mix-bottom="#toast">{ toast_ok }</browser>
        <browser mix-top="#comments-{post_pk}">{html_comment}</browser>
        """
    except Exception as ex:
        if "x-error post" in str(ex):
            toast_error = render_template("___toast_error.html", message=x.lans("invalid_post_length"))
            return f"""<browser mix-bottom="#toast">{toast_error}</browser>"""

        ic(ex)
        toast_error = render_template("___toast_error.html", message=x.lans("system_under_maintenance"))
        return f"""<browser mix-bottom="#toast">{ toast_error }</browser>""", 500
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()    


##############################

@app.route("/api-update-profile", methods=["POST"])
def api_update_profile():
    try:
        user = session.get("user", "")
        if not user: 
            return "invalid user"

        user_email = x.validate_user_email()
        user_username = x.validate_user_username()
        user_first_name = x.validate_user_first_name()
        user_bio = request.form.get("user_bio", "").strip()

        uploaded_file = request.files.get("user_avatar")
        user_avatar_path = user.get("user_avatar_path", "")

        if uploaded_file and uploaded_file.filename:
            filename = secure_filename(uploaded_file.filename)
            file_ext = os.path.splitext(filename)[1].lower()

            if file_ext not in current_app.config['UPLOAD_EXTENSIONS']:
                raise Exception("File type not allowed", 400)

            filename = f"user_{user['user_pk']}_avatar{file_ext}"

            upload_folder = current_app.config['UPLOAD_FOLDER']
            upload_folder.mkdir(parents=True, exist_ok=True)

            save_path = upload_folder / filename
            uploaded_file.save(save_path)

            user_avatar_path = filename

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

        user["user_email"] = user_email
        user["user_username"] = user_username
        user["user_first_name"] = user_first_name
        user["user_bio"] = user_bio
        user["user_avatar_path"] = user_avatar_path
        session["user"] = user

        toast_ok = render_template("___toast_ok.html", message=x.lans("profile_updated_successfully"))

        return f"""
            <browser mix-bottom="#toast">{toast_ok}</browser>
            <browser mix-update="#profile_tag .name">{user_first_name}</browser>
            <browser mix-update="#profile_tag .handle">@{user_username}</browser>
            <browser mix-update="#profile_bio">{user_bio}</browser>
        """, 200
    
    except Exception as ex:
        ic(ex)

        if isinstance(ex, RequestEntityTooLarge):
            toast_error = render_template(
                "___toast_error.html",
                message="File too large. Maximum size is 4 MB"
            )
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400

        if len(ex.args) > 1 and ex.args[1] == 400:
            toast_error = render_template("___toast_error.html", message=ex.args[0])
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400
        
        if "Duplicate entry" in str(ex) and user_email in str(ex): 
            toast_error = render_template("___toast_error.html", message=x.lans("email_already_registered"))
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400
        if "Duplicate entry" in str(ex) and user_username in str(ex): 
            toast_error = render_template("___toast_error.html", message=x.lans("username_already_registered"))
            return f"""<mixhtml mix-update="#toast">{ toast_error }</mixhtml>""", 400
        
        toast_error = render_template("___toast_error.html", message=x.lans("system_under_maintenance"))
        return f"""<mixhtml mix-bottom="#toast">{ toast_error }</mixhtml>""", 500

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################
@app.post("/api-search")
def api_search():
    try:
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

##############################

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

@app.patch("/admin-block-post/<post_pk>")
def admin_block_post(post_pk):
    try:
        admin = session.get("user", "")
        if not admin:
            return "No user found"

        if admin.get("user_is_admin") != 1:
            return "Not allowed for non-admin users.", 400

        db, cursor = x.db()
        q = "SELECT * FROM posts WHERE post_pk = %s"
        cursor.execute(q, (post_pk,))
        post = cursor.fetchone()

        if not post:
            toast = render_template("___toast_error.html", message=x.lans("post_not_found"))
            return f"""<browser mix-bottom="#toast">{toast}</browser>"""

        current_state = post["post_is_blocked"]
        new_state = 1 if current_state == 0 else 0

        q = "UPDATE posts SET post_is_blocked = %s WHERE post_pk = %s"
        cursor.execute(q, (new_state, post_pk))
        db.commit()

        q = """
        SELECT users.user_email
        FROM users
        JOIN posts ON users.user_pk = posts.post_user_fk
        WHERE posts.post_pk = %s
        """
        cursor.execute(q, (post_pk,))
        owner = cursor.fetchone()

        if owner:
            if new_state == 1:
                email_html = "Your post has been blocked by an administrator."
                x.send_email(owner["user_email"], "Post Blocked", email_html)
                toast = render_template("___toast_ok.html", message=x.lans("post_is_now_blocked"))
            else:
                email_html = "Your post has been unblocked by an administrator."
                x.send_email(owner["user_email"], "Post Unblocked", email_html)
                toast = render_template("___toast_ok.html", message=x.lans("post_is_now_unblocked"))

        updated_button = render_template(
            "__admin_toggle_post_button.html", 
            tweet={**post, "post_is_blocked": new_state}
        )

        return f"""
            <browser mix-bottom="#toast">{toast}</browser>
            <browser mix-remove="#comment-form-{post_pk}"></browser>
            <browser mix-remove="#comments-{post_pk}"></browser>
            <browser mix-replace="#toggle-post-{post_pk}">{updated_button}</browser>
            <browser mix-remove="#tweet-{post_pk}"></browser>
        """

    except Exception as ex:
        ic(ex)
        toast = render_template("___toast_error.html", message="System Error")
        return f"""<browser mix-bottom="#toast">{toast}</browser>"""

    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()


##############################

@app.patch("/admin-block-user")
def admin_block_user():
    try:
        admin = session.get("user", "")
        if not admin:
            return "No admin user found"

        if admin.get("user_is_admin") != 1:
            return "Not allowed for non-admin users.", 400

        user_pk = request.form.get("block-user-input", "").strip()
        ic(user_pk)

        db, cursor = x.db()

        q = "SELECT * FROM users WHERE user_pk = %s"
        cursor.execute(q, (user_pk,))
        user = cursor.fetchone()

        if not user:
            toast = render_template("___toast_error.html", message=x.lans("user_does_not_exist"))
            return f"""<browser mix-bottom="#toast">{toast}</browser>"""

        is_blocked = user["user_is_blocked"]

        new_state = 1 if is_blocked == 0 else 0

        q = "UPDATE users SET user_is_blocked = %s WHERE user_pk = %s"
        cursor.execute(q, (new_state, user_pk))
        db.commit()

        if new_state == 1:
            email_html = "Your account has been blocked by an administrator."
            x.send_email(user["user_email"], "Account Blocked", email_html)
            toast = render_template("___toast_ok.html", message=x.lans("user_is_now_blocked"))
        else:
            email_html = "Your account has been unblocked by an administrator."
            x.send_email(user["user_email"], "Account Unblocked", email_html)
            toast = render_template("___toast_ok.html", message=x.lans("user_is_now_unblocked"))

        updated_button_html = render_template(
            "__admin_toggle_user_button.html",
            user={**user, "user_is_blocked": new_state}
        )

        return f"""
            <browser mix-bottom="#toast">{toast}</browser>
            <browser mix-replace="#toggle-user-{user_pk}">{updated_button_html}</browser>
        """

    except Exception as ex:
        ic(ex)
        toast = render_template("___toast_error.html", message="System Error")
        return f"""<browser mix-bottom="#toast">{toast}</browser>"""

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
        dict_path = BASE_DIR / "dictionary.json"
        with dict_path.open("w", encoding="utf-8") as f:
            f.write(json_data)

        return "ok"
    except Exception as ex:
        ic(ex)
        return str(ex)
    finally:
        pass

##############################

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

            reset_url = f"{domain}/reset-password/{reset_key}"
            email_html = f'To reset your password, click here: <a href="{reset_url}">Reset password</a>'
            x.send_email(user_email, "Reset your password", email_html)

            toast_ok = render_template("___toast_ok.html", message=x.lans("password_reset_email_sent"))
            return f"""
            <browser mix-bottom="#toast">{ toast_ok }</browser>
            """

        except Exception as ex:
            toast = render_template("___toast_error.html", message=ex.args[0])
            return f"<browser mix-update='#toast'>{toast}</browser>", 400
        
        finally:
            if "cursor" in locals(): cursor.close()
            if "db" in locals(): db.close()

##############################

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

##############################

@app.get("/<username>")
def user_profile(username):
    try:
        session_user = session.get("user", "")
        if not session_user:
            return redirect(url_for("login"))

        db, cursor = x.db()
        q = """SELECT 
            users.*,
            EXISTS(
                SELECT 1 
                FROM follows 
                WHERE follows.user_fk = users.user_pk
                AND follows.follower_fk = %s
            ) AS followed
        FROM users
        WHERE users.user_username = %s
        LIMIT 1;
        """
        cursor.execute(q, (session_user["user_pk"], username,))
        user = cursor.fetchone()
        if not user:
            return "error user not found"

        tweets = grab_tweets(useronly=True, target_user_pk=user["user_pk"])

        is_me = session_user["user_pk"] == user["user_pk"]

        profile_html = render_template("_profile.html", user=user, tweets=tweets, is_me=is_me)

        return f"""<browser mix-update="main">{ profile_html }</browser>"""

    except Exception as ex:
        ic(ex)
        return "error"
    finally:
        if "cursor" in locals(): cursor.close()
        if "db" in locals(): db.close()

##############################

@app.get("/admin")
def get_admin():
    try:
        user = session.get("user", "")

        if user["user_is_admin"] == 0:
            return redirect(url_for("home"))
        db, cursor = x.db()
        tweets = grab_tweets(blockedonly=True)
        q = "SELECT * FROM users WHERE user_is_blocked = 1"
        cursor.execute(q,)
        blocked_users = cursor.fetchall()
        ic(blocked_users)
        html = render_template("_admin.html", tweets=tweets, user=user, blocked_users=blocked_users)
        return f"""<browser mix-update="main">{html}</browser> """
    except Exception as ex:
        ic(ex)
        return "error"
    finally:
        pass

##############################

@app.get("/grok")
def get_grok():
    try:
        user = session.get("user", "")
        if not user:
            return "error"

        html = render_template("_grok.html", user=user)
        return f"""<mixhtml mix-update="main">{ html }</mixhtml>"""
    except Exception as ex:
        ic(ex)
        return "error"
    finally:
        pass