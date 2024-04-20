from flask import Flask, redirect, url_for, render_template, request, session, flash
from datetime import timedelta, datetime
from flask_sqlalchemy import SQLAlchemy
from werkzeug.utils import secure_filename
from PIL import Image
import math, bcrypt, os, glob


app = Flask(__name__)
app.secret_key = ("pretendthisisarealsecretkey")

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.sqlite3'
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
app.permanent_session_lifetime = timedelta(hours=5)
db = SQLAlchemy(app)

UPLOAD_FOLDER = 'static/avatars'
ALLOWED_EXTENSIONS = {'png'} 
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 1024 * 1024 #1MB


#TODO
'''
- profile pics for users
    - verify that img is 8x8
    - default pic
- email verification stuff
- forum moderation
    - only post once/ 5 sec
- search through posts
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
    '''
    warning! turns out when you delete all the posts from the db bc you get bored and want to break things, it actually does break things. careful!
    '''
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

'''class tags(db.Model): #DONT ADD TAGS YET THEYRE HARD
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

def verifyregister(uname, upass, uemail): #this could be better
    '''
    Checks if password, username, email strings fit within 
    desired parameters, e.g. length. 
    probably should be the function that hashes passwords, but isn't. don't look for password hashing here, it's in @app.route(/"register"). and login
    '''
    existinguser = users.query.filter_by(name=uname).first() 
    existingemail = users.query.filter_by(email=uemail).first()

    if existinguser or existingemail:
        flash("ur username or email already exists")
        return False

    if "." not in uemail:
        if "@" not in uemail:
            print(uemail)
            flash("that's not an email, stupid")
            return False

    if len(uname) < 4:
        flash("username must be at least 4 characters")
        return False
    elif len(uname) > 20:
        flash("username must be fewer than 20 characters")
        return False
            
    if len(upass) < 7:
        flash("try a longer password. mininum 7 characters")
        return False
    elif len(upass) > 20:
        flash("password must be fewer than 20 characters")
        return False
    
    print("verified new user")

def round_seconds(obj: datetime) -> datetime:
    '''
    just a feature that should probably be in the datetime package already, but i've gotta do it manually :(
    '''
    if obj.microsecond >= 500_000:
        obj += timedelta(seconds=1)
    return obj.replace(microsecond=0)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def home():
    username = "Not signed in"
    if "user" in session:
        username = session['user']
    return(render_template("main.html", username=username))

@app.route("/feed", methods=['GET', 'POST']) 
def feed():
    postcount = posts.query.order_by(posts.date.desc()).count()
    postcount = int(math.ceil(postcount / 10.0)) - 1 # get the most recent page of posts
    return redirect(url_for("feedposts", page=postcount))

@app.route("/feed/<page>", methods=['GET', 'POST'])
def feedposts(page):
    try:
        intpage = int(page)
    except ValueError:
        flash("Try it with an integer!")
        return redirect(url_for("feed"))

    if intpage < 0:
        intpage = int(0)
        
    ppg = int(10) # posts per page, int() bc trust issues

    offset = (ppg * intpage)
    shownposts = posts.query.order_by(posts.date.asc()).offset(offset).limit(ppg)

    activepage = (int(math.ceil(posts.query.order_by(posts.date.desc()).count() / ppg)) - 1)
    
    if activepage < 0:
        activepage = 0

    if intpage == activepage: #if this is the page with the most recent posts :) 
        mostrecent = True
    elif intpage > activepage:
        flash("Do not dwell on the future. Turn your head and live fully in the present.")
        return redirect(url_for("feed"))
    else:
        mostrecent = False

    if request.method == 'POST':
        if "user" not in session:
            flash("You must log in to post!")
            return redirect(url_for("login"))
        else:
            username = session['user']
        newpost = posts(session['user'], request.form.get('content'), request.form.get('imglink'), round_seconds(datetime.now()))
        db.session.add(newpost) 
        db.session.commit()
        print("post created by {username}".format(username=username))
        return redirect(url_for("feed"))
    
    return render_template("feed.html", shownposts=shownposts, intpage=intpage, mostrecent=mostrecent)

@app.route('/userpages/<user>', methods=['GET', 'POST'])
def userpages(user):
    '''
    idk why i didn't just call it profiles, thats really what it is. eh.
    '''
    user = users.query.filter_by(name=user).first()

    if request.method == 'POST':
        if request.files['file']:
            print("file good")
        else:
            flash("Don't be stupid, upload an actual file")
            return redirect(url_for("home"))
        
        file = request.files['file']

        if file and allowed_file(file.filename):
            # check if file is a png, check that file is 8x8, check size is ok
            filename = (user.name + ".png")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            print("file saved")
            with Image.open("static/avatars/{filename}".format(filename=filename)) as im:
                newsize = (8,8)
                im = im.resize(newsize)
                im.save("static/avatars/{filename}".format(filename=filename))
                print("img resized to 8x8")
            return redirect(url_for('userpages', user=user.name))

    postcount = posts.query.filter_by(op=user.name).count()
    avatarloc = "{userr}.png".format(userr=user.name)

    isme = False
    if user == None:
        flash("No user with that name!")
        return redirect(url_for("home"))
    elif 'user' in session:
        if user.name == session['user']:
            isme = True


    return render_template("userpage.html", user=user, postcount=postcount, avatarloc=avatarloc, isme=isme)

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
            if bcrypt.checkpw(str.encode(foundpass), founduser.password):
                session["user"] = founduser.name
                flash("loggied in successfully")
                return redirect(url_for("home"))
            else:
                flash("wrong password")
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
            return redirect(url_for("home")) 
        
        uname = request.form.get('username')
        uemail = request.form.get('email')
        hashedupass = bcrypt.hashpw(str.encode(request.form.get('password')), bcrypt.gensalt())

        if verifyregister(uname, request.form.get('password'), uemail) == False:
            return redirect(url_for("home"))
        
        newuser = users(uname, uemail, hashedupass)
        db.session.add(newuser) #i'm in
        db.session.commit()

        currentuser = users.query.filter_by(name=newuser.name).first()
        session["user"] = currentuser.name #welcome to the sesh
        flash("loggied in, account created. welcome!")

        return redirect(url_for("home"))
    # else:
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