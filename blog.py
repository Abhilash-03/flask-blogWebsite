from flask import Flask, render_template, request, session, redirect
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail
from werkzeug.utils import secure_filename
import json
import os
import math
from datetime import datetime

"""Read a file from config.json """
with open("config.json", 'r') as c:
    params = json.load(c)["params"]

local_server = 'True'

app = Flask(__name__)

app.secret_key = 'super-secret-key'

app.config['UPLOAD_FILE'] = params['upload_location']

# sending a message via gmail this is the way down below ⬇  ️
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT='465',
    MAIL_USE_SSL=True,
    MAIL_USERNAME=params['gmail-user'],
    MAIL_PASSWORD=params['gmail-password'],
)

mail = Mail(app)

if local_server:
    app.config['SQLALCHEMY_DATABASE_URI'] = params['local_uri']
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = params['prod_uri']

db = SQLAlchemy(app)


class Contact(db.Model):
    Sno = db.Column(db.Integer, primary_key=True)
    Name = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(20), nullable=False)
    phone = db.Column(db.String(12), nullable=False)
    msg = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(12), nullable=True)


class Posts(db.Model):
    sno = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(50), nullable=False)
    tagline = db.Column(db.String(50), nullable=False)
    slug = db.Column(db.String(30), nullable=False)
    content = db.Column(db.String(120), nullable=False)
    date = db.Column(db.String(12), nullable=True)
    img_file = db.Column(db.String(12), nullable=True)


@app.route("/")
def home():
    # Pagination Logic

    posts = Posts.query.filter_by().all()

    last = math.ceil(len(posts) / int(params['no_of_posts']))
    page = request.args.get('page')
    if not str(page).isnumeric():
        page = 1

    page = int(page)

    # ---------------both logic of pagination is correct.------------------------------

    # posts = posts[(page - 1) * int(params['no_of_posts']): (page - 1) * int(params['no_of_posts']) + int(
    #     params['no_of_posts'])]

    j = (page - 1) * int(params['no_of_posts'])
    posts = posts[j:j + int(params['no_of_posts'])]  # +int(params['no_of_posts']) means how many posts we want on home
    # page

    if page == 1:
        prev = "#"
        next_page = "/?page=" + str(page + 1)

    elif page == last:
        prev = "/?page=" + str(page - 1)
        next_page = "#"

    else:
        prev = "/?page=" + str(page - 1)
        next_page = "/?page=" + str(page + 1)

    # posts = Posts.query.filter_by().all()[0:params['no_of_posts']]
    return render_template('index.html', params=params, posts=posts, prev=prev, next=next_page)


@app.route("/about")
def about():
    return render_template('about.html', params=params)


@app.route("/dashboard", methods=['GET', 'POST'])
def dashboard():
    # this first line tell us that user is logged in
    if 'user' in session and session['user'] == params['admin_user']:
        posts = Posts.query.all()

        return render_template('dashboard.html', params=params, posts=posts)

    if request.method == 'POST':
        username = request.form.get("uname")
        userpass = request.form.get("pass")

        if username == params["admin_user"] and userpass == params["admin_password"]:
            #  set the session variable
            session['user'] = username
            posts = Posts.query.all()
            return render_template('dashboard.html', params=params, posts=posts)

    else:
        return render_template('login.html', params=params)


@app.route("/post/<string:post_slug>/", methods=['GET'])
def post_route(post_slug):
    post = Posts.query.filter_by(slug=post_slug).first()

    return render_template('post.html', params=params, post=post)


@app.route("/edit/<string:sno>/", methods=['GET', 'POST'])
def edit(sno):
    if "user" in session and session['user'] == params['admin_user']:
        if request.method == "POST":

            box_title = request.form.get('title')
            tagline = request.form.get('tagline')
            slug = request.form.get('slug')
            content = request.form.get('content')
            img_file = request.form.get('img_file')
            date = datetime.now()

            # if we want to add new post in post then do this
            if sno == '0':
                post = Posts(title=box_title, slug=slug, content=content, tagline=tagline, img_file=img_file, date=date)
                db.session.add(post)
                db.session.commit()
            # else if we want to edit existing post in post then do this
            else:
                post = Posts.query.filter_by(sno=sno).first()
                post.title = box_title
                post.slug = slug
                post.content = content
                post.tagline = tagline
                post.img_file = img_file
                post.date = date
                db.session.commit()
                return redirect('/edit/' + sno)
        post = Posts.query.filter_by(sno=sno).first()
        return render_template('edit.html', params=params, post=post, sno=sno)


@app.route("/delete/<string:sno>/", methods=['GET', 'POST'])
def delete(sno):
    if 'user' in session and session['user'] == params['admin_user']:
        post = Posts.query.filter_by(sno=sno).first()
        db.session.delete(post)
        db.session.commit()
        return redirect("/dashboard")


@app.route("/uploader", methods=['GET', 'POST'])
def uploader():
    # First will be checked that user is logged in or not if he is, then he can change the files
    # else he can't change the files
    if 'user' in session and session['user'] == params['admin_user']:
        if request.method == 'POST':
            f = request.files['files']
            f.save(os.path.join(app.config['UPLOAD_FILE'], secure_filename(f.filename)))
            return "Uploaded file successfully!!"


@app.route("/logout")
def logout():
    session.pop('user')
    return redirect("/dashboard")


@app.route("/contact", methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        """ Add entry to the database """
        name = request.form.get('name')
        email = request.form.get('email')
        phone = request.form.get('phone')
        message = request.form.get('message')

        entry = Contact(Name=name, email=email, phone=phone, msg=message, date=datetime.now())
        db.session.add(entry)
        db.session.commit()
        mail.send_message("New message from " + name,
                          sender=email,
                          recipients=[params['gmail-user']],
                          body=message + '\n' + "Phone no: " + phone
                          )

    return render_template('contact.html', params=params)


app.run(debug=True)
