from flask import Flask, redirect, url_for, render_template, request, session, flash
from datetime import timedelta, datetime
from flask_sqlalchemy import SQLAlchemy
import math

app = Flask(__name__)
app.secret_key = ("Ilovemysecretkey")

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.sqlite3'
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.permanent_session_lifetime = timedelta(hours=5)

db = SQLAlchemy(app)

#TODO
'''
- combine post maker and post viewer into a popup kinda thing
- likes/dislikes for posts
- user profile? 
- search through posts
- better post creation ui, post viewing ui
'''

class users(db.Model):
    _id = db.Column("id", db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True) #not using a string name for these bc it just uses the var name as a default
    email = db.Column(db.String(100), unique=True)
    password = db.Column(db.String(100))

    def __init__(self, name, email, password):
        self.name = name
        self.email = email
        self.password = password

class posts(db.Model):
    _id = db.Column("id", db.Integer, primary_key=True)
    op = db.Column(db.String(100))
    content = db.Column(db.String)
    imglink = db.Column(db.String)
    date = db.Column(db.String)

    def __init__(self, op, content, imglink, date):
        self.op = op
        self.content = content
        self.imglink = imglink
        self.date = date

'''class tags(db.Model): #DONT ADD TAGS YET THEYRE HARDDDD
    _id = db.Column("id", db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True)

    def __init__(self, name):
        self.name = name

# now THIS is podracing
class tagmap(db.Model):
    _id = db.Column("id", db.Integer, primary_key=True)
    post_id = db.Column(db.Integer)
    tag_id = db.Column(db.Integer)

    def __init__(self, post_id, tag_id):
        self.post_id = post_id
        self.tag_id = tag_id'''


def verifyregister(uname, upass, uemail):
    '''
    Checks if password, username, email strings fit within 
    desired parameters, e.g. length.
    '''
    existinguser = users.query.filter_by(name=uname).first() 
    existingemail = users.query.filter_by(email=uemail).first()

    if existinguser or existingemail:
        flash("ur username or email already exists")
        return False

    if all(x in uemail for x in [".", "@"]):
        flash("that's not an email, stupid")
        return False

    if len(uname) < 4:
        flash("username must be at least 4 characters")
        return False
            
    if len(upass) < 7:
        flash("Error! Password too short? get it? at least 7 characters pls")
        return False
    
    print("verified new user")

def round_seconds(obj: datetime) -> datetime:
    if obj.microsecond >= 500_000:
        obj += timedelta(seconds=1)
    return obj.replace(microsecond=0)

@app.route("/")
def home():
    username = "Not signed in"
    if "user" in session:
        username = session['user']
    return(render_template("main.html", username=username))

@app.route("/post", methods=['GET', 'POST'])
def post():
    if "user" not in session:
        flash("You must log in to post!")
        return redirect(url_for("login"))
    else:
        username = session['user']

    if request.method == 'POST':
        newpost = posts(session['user'], request.form.get('content'), request.form.get('imglink'), round_seconds(datetime.now()))
        db.session.add(newpost) 
        db.session.commit()
        print(session['user'])
        print("made a post")
        flash("Post sucessfully created!")
        return redirect(url_for("feed"))
    return render_template("post.html", username=username)

@app.route("/feed", methods=['GET', 'POST']) # add a fricking next page button
def feed():
    postcount = posts.query.order_by(posts.date.desc()).count()
    postcount = int(math.ceil(postcount / 10.0)) - 1 # get the most recent page of posts
    return redirect(url_for("feedposts", page=postcount))

@app.route("/feed/<page>", methods=['GET'])
def feedposts(page):
    try:
        intpage = int(page)
    except ValueError:
        flash("Try it with an integer!")
        return redirect(url_for("feed"))
    
    if intpage < 0:
        return redirect(url_for("feedposts", page=0))
    offset = (10 * intpage) #10 posts per page makes money for days
    shownposts = posts.query.order_by(posts.date.asc()).offset(offset).limit(10)
    backpage = intpage - 1  # currently unused
    forwardpage = intpage + 1  # currently unused
    return render_template("feed.html", shownposts=shownposts, intpage=intpage, backpage=backpage, forwardpage=forwardpage)


@app.route('/pageturn', methods=['GET', 'POST'])
def pageturn():
    banana = request.referrer
    peeledbanana = banana.split("/")
    page = (int(peeledbanana[4]) + 1) # https: /  / feed / {number}, 3 slashes
    return redirect(url_for("feedposts", page=page))

@app.route('/backpageturn', methods=['GET', 'POST'])
def backpageturn():
    banana = request.referrer
    peeledbanana = banana.split("/")
    page = (int(peeledbanana[4]) - 1) # https: /  / feed / {number}, 3 slashes
    return redirect(url_for("feedposts", page=page))


@app.route("/login", methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        founduser = users.query.filter_by(name=request.form.get('username')).first()
        foundpass = request.form['password'] # i think this is the same as request.form.get('password')
        if founduser:
            if foundpass!=founduser.password:
                flash("wrong password")
                return redirect(url_for("home"))
            else:
                session["user"] = founduser.name
                flash("loggied in successfully")
                return redirect(url_for("home"))
        else:
            flash("no account found with that username")
            return redirect(url_for("home"))
    else:
        if "user" in session:
            flash("already loggied in")
            return redirect(url_for("home"))
        
    return render_template("login.html")

@app.route("/register", methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        if request.form.get('password')!=request.form.get('passwordverify'):
            flash("password no matchy")
            return redirect(url_for("home")) # set up flash later idk but this means they gotta mismatched password
        
        uname = request.form.get('username')
        uemail = request.form.get('email')

        if verifyregister(uname, request.form.get('password'), uemail) == False:
            print("user not verified")
            return redirect(url_for("home"))
            

        newuser = users(uname, uemail, request.form.get('password'))
        db.session.add(newuser) #ur in
        db.session.commit()

        currentuser = users.query.filter_by(name=newuser.name).first()
        session["user"] = currentuser.name #welcome to the sesh
        flash("loggied in, account created. welcome!")
        print(currentuser)

        return redirect(url_for("home"))
    
    return(render_template("register.html"))

@app.route("/logout")
def logout():
    flash("you have been loggied out")
    session.pop("user", None)
    return redirect(url_for("login"))

@app.errorhandler(404)
def page_not_found(e):
    return render_template("404.html", attempt=e)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)