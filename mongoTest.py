from flask import Flask, render_template, request, session, redirect, flash
from werkzeug.utils import secure_filename
from flask_pymongo import PyMongo
from datetime import datetime
from flask_mail import Mail
import json
import os
import math
import bcrypt



with open('config.json','r') as c:
    params = json.load(c)['params']


class DataStore():
    login = False
obj = DataStore()



local_server = True
app = Flask(__name__)
app.secret_key = 'super-secret-key'
app.config['UPLOAD_FOLDER'] = params['upload_location']



app.config.update(
MAIL_SERVER = 'smtp.gmail.com',
MAIL_PORT = 465,
MAIL_USE_SSL  = True,
MAIL_USERNAME = params['Mail-user'],
MAIL_PASSWORD = params['Mail-password']
)
mail = Mail(app)



if local_server:
    app.config["MONGO_URI"] = params['local_uri_MDB']
else:
    app.config["MONGO_URI"] = params['prod_uri_MDB']



mongo = PyMongo(app)
db = mongo.db
collection = db.Contacts
collection1 = db.posts



@app.route('/')
@app.route('/home')
def Home():
    posts = collection1.find()
    noOfPost = collection1.count_documents({})
    last = math.ceil(noOfPost/ int(params['no_of_posts']))
    page = request.args.get('page')
    if(not str(page).isnumeric()):
        page = 1
    page = int(page)
    posts=posts[(page-1)*int(params['no_of_posts']):(page-1)*int(params['no_of_posts'])+int(params['no_of_posts'])]

    if( page == 1):
        prev = "#"
        next = "/?page=" + str(page + 1)
    elif( page == last):
        prev = "/?page=" + str(page - 1)
        next = "#"
    else:
        prev = "/?page=" + str(page - 1)
        next = "/?page=" + str(page + 1)
    return render_template('index.html', params=params, posts = posts , prev = prev , next = next, login = obj.login)



@app.route('/about')
def About():
    return render_template('about.html', params=params, login = obj.login)



@app.route('/contact', methods=["GET","POST"])
def Contact():
    if request.method == "POST":
        name = request.form['name']
        email = request.form['email']
        phone = request.form['phone']
        message = request.form['message']
        data = {"name":name, "phone_num":phone, "msg":message, "date": datetime.now(), "email":email}
        doc = collection.insert(data)
        mail.send_message('New message from ' + name ,
                          sender=email,
                          recipients=[params['Mail-user']],
                          body = message + "\n" + phone
        )
        flash("Thanks for contacting us, we will get back to you", "success")
    return render_template('contact.html', params=params, login = obj.login)



@app.route('/dashboard', methods=["GET","POST"])
def Login():
    if ('user' in session and session['user'] == params['admin_user']):
        obj.login = True
        posts = collection1.find()
        return render_template('dashboard.html', params=params, posts = posts, login = obj.login)
    if request.method == "POST":
        username = request.form['uname']
        userpass = request.form['pass']
        if (username == params['admin_user'] and userpass == params['admin_password']):
            obj.login = True
            session['user'] = username
            posts = collection1.find()
            return render_template('dashboard.html', params=params, posts = posts, login = obj.login)
    return render_template('login.html', params=params)



@app.route("/addpost",methods=['GET','POST'])
def Insert():
    if ('user' in session and session['user'] == params['admin_user']):
        if request.method == "POST":
            title = request.form['title']
            tagline = request.form['tline']
            slug = request.form['slug']
            content = request.form['content']
            img_file = request.form['img_file']
            count = collection1.count_documents({})
            if count == 0:
                next_sno = 1
            else:
                result = collection1.find({}).sort([("sno", 1)]).skip(count - 1).limit(1)
                next_sno = 0
                for x in result:
                    next_sno = x["sno"]
                if next_sno == 0:
                    next_sno = 1
                else:
                    next_sno = next_sno +1

            data = {"sno": next_sno, "title": title, "tagline": tagline, "slug": slug, "content": content,
                        "img_file": img_file,"date": datetime.now()}
            collection1.insert_one(data)
            flash("Post Added Successfully", "success")
            return redirect('/dashboard')
        return render_template('insert.html', params=params, login = obj.login)



@app.route("/delete/<string:sno>",methods=['GET','POST'])
def delete(sno):
    if ('user' in session and session['user'] == params['admin_user']):
        serial_no = int(sno)
        collection1.delete_one({"sno": serial_no})
        flash("Post Deleted Successfully", "success")
    return redirect('/dashboard')



@app.route("/edit/<string:sno>",methods=['GET','POST'])
def Edit(sno):
    if ('user' in session and session['user'] == params['admin_user']):
        serial_no = int(sno)
        if request.method == "POST":
            title = request.form['title']
            tagline = request.form['tline']
            slug = request.form['slug']
            content = request.form['content']
            img_file = request.form['img_file']
            query = {"sno": serial_no}
            data = {"$set": { "title": title, "tagline": tagline, "slug": slug, "content": content, "img_file": img_file, "date": datetime.now()} }
            collection1.update_one(query, data)
            return redirect('/dashboard')
        post = collection1.find_one({"sno": serial_no})
        return render_template('edit.html', params=params, post=post, login = obj.login)



@app.route("/post/<string:post_slug>",methods=["GET"])
def Post_route(post_slug):
    post = collection1.find_one({ "slug" : post_slug})
    return render_template('post.html', params=params, post=post, login = obj.login)



@app.route('/uploader', methods=["GET","POST"])
def Upload():
    if ('user' in session and session['user'] == params['admin_user']):
        if request.method == "POST":
            uplodedFile = request.files['uplodedFile']
            uplodedFile.save(os.path.join(app.config['UPLOAD_FOLDER'], secure_filename(uplodedFile.filename)))
            flash("File Uploaded Successfully", "success")
        return redirect('/dashboard')



@app.route('/logout')
def Logout():
    if ('user' in session and session['user'] == params['admin_user']):
        session.pop('user')
        obj.login = False
    return redirect('/home')



app.run(debug=True)