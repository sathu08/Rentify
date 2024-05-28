from lib_file import *

with open("path_file/database.txt") as f:
    database = f.read()
credentials = {}
with open('credentials_details/credentials.txt') as file:
    for line in file:
        key, value = line.strip().split('=')
        credentials[key] = value
with open('email_body/create_account.txt') as file:
    create_body = file.read()
with open('email_body/otp_body.txt') as file:
    otp_body = file.read()
with open('email_body/show_interest.txt') as file:
    show_interest = file.read()
app = Flask(__name__)
app.secret_key = secrets.token_hex(16)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
details_path = ''
current_login_id = ''
login_type = False
current_date = datetime.date(datetime.now())
current_time = datetime.time(datetime.now())


def time_counter():
    global login_type
    # 300 s is 10 m
    seconds = 600
    while seconds > 0:
        time.sleep(1)
        seconds -= 1
    login_type = False


def start_time_counter():
    thread = threading.Thread(target=time_counter)
    thread.daemon = True
    thread.start()


def get_db_connection():
    conn = sqlite3.connect(database)
    conn.row_factory = sqlite3.Row
    return conn


def send_email(receiver_email, subject, body):
    sender_email = credentials['sender_email']
    password = credentials['password']
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    try:
        server = smtplib.SMTP("smtp.gmail.com", 587)
        server.starttls()
        server.login(sender_email, password)
        server.sendmail(sender_email, receiver_email, msg.as_string())
        print("Email sent successfully!")
    except Exception as e:
        print(f"Failed to send email: {e}")
    finally:
        server.quit()


class User(UserMixin):
    def __init__(self, id):
        self.id = id

    @staticmethod
    def get(user_id):
        return User(user_id)


@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)


@app.route('/')
def login_pass():
    global login_type
    user = User.get(socket.gethostbyname(socket.gethostname()))
    login_user(user)
    login_type = False
    return redirect(url_for('home'))


@app.route('/home', methods=['GET', 'POST'])
@login_required
def home():
    global details_path, login_type
    seller_detail = request.args.get('seller_details')
    conn = sqlite3.connect(database)
    cursor = conn.cursor()
    results = cursor.execute(
        'SELECT area, bedrooms, bathroom, type_of_buildings, places, product_id FROM rentify_details').fetchall()
    product_id = [result[5] for result in results]
    type_of_building = [result[4] for result in results]
    if seller_detail:
        details_path = seller_detail
        return redirect(url_for('seller_details'))
    image_data = cursor.execute("SELECT img_1 FROM rentify_details").fetchall()
    conn.close()
    image_urls = []
    for data in image_data:
        if data[0]:
            if isinstance(data[0], str):
                image_data_bytes = data[0].encode('utf-8')
            else:
                image_data_bytes = data[0]
            image_data_base64 = base64.b64encode(image_data_bytes).decode('utf-8')
            image_urls.append(f"data:image/jpeg;base64,{image_data_base64}")
    if request.method == 'POST':
        query = request.form['query']
        if query:
            conn = sqlite3.connect(database)
            cursor = conn.cursor()
            results = cursor.execute(
                "SELECT area, bedrooms, bathroom, type_of_buildings, places, seller_id FROM rentify_details "
                "WHERE area LIKE ? OR places LIKE ? OR bedrooms LIKE ? OR bathroom LIKE ? OR near_by LIKE ? "
                "OR type_of_buildings LIKE ?",
                ('%' + query + '%', '%' + query + '%', '%' + query + '%', '%' + query + '%', '%' + query + '%',
                 '%' + query + '%')).fetchall()
            fetch_result = [result[0] for result in results]
            product_id = [result[5] for result in results]
            type_of_building = [result[4] for result in results]
            if not fetch_result:
                flash("No data matched your query.")
                return redirect(url_for('home'))
            image_urls = []
            for result in fetch_result:
                cursor.execute("SELECT img_1 FROM rentify_details WHERE area LIKE ?", ('%' + result + '%',))
                image_data = cursor.fetchall()
                for data in image_data:
                    if data[0]:
                        if isinstance(data[0], str):
                            image_data_bytes = data[0].encode('utf-8')
                        else:
                            image_data_bytes = data[0]
                        image_data_base64 = base64.b64encode(image_data_bytes).decode('utf-8')
                        image_urls.append(f"data:image/jpeg;base64,{image_data_base64}")
            conn.close()
        return render_template('home.html', image_urls=image_urls, product_id=product_id,
                               type_of_building=type_of_building, search_value=query, user=login_type)
    return render_template('home.html', image_urls=image_urls, product_id=product_id,
                           type_of_building=type_of_building, user=login_type)


@app.route('/seller_details', methods=['GET', 'POST'])
@login_required
def seller_details():
    global details_path, login_type, current_login_id
    share_details = request.args.get('share_details')
    if login_type:
        conn = sqlite3.connect(database)
        cursor = conn.cursor()
        image_data = cursor.execute('SELECT img_1,img_2,img_3,img_4,img_5 FROM rentify_details where product_id = ?',
                                    (details_path,)).fetchall()
        image_urls = []
        for data in image_data:
            if data[0]:
                if isinstance(data[0], str):
                    image_data_bytes = data[0].encode('utf-8')
                else:
                    image_data_bytes = data[0]
                image_data_base64 = base64.b64encode(image_data_bytes).decode('utf-8')
                image_urls.append(f"data:image/jpeg;base64,{image_data_base64}")
        results = cursor.execute('SELECT places, area, bedrooms, bathroom, type_of_buildings,seller_id '
                                 'FROM rentify_details where product_id = ?', (details_path,)).fetchall()

        if share_details:
            seller_id = [ids[5] for ids in results]
            current_login_user = cursor.execute('select * from login_details where user_id = ?', (current_login_id,)).fetchone()
            seller_name = cursor.execute('select first_name, email_id from login_details where user_id = ?', (seller_id[0],)).fetchone()
            print(current_login_user)
            print(seller_name)
            subject = "Prospective Client Interest"
            body = show_interest.replace("User", seller_name[0])
            body = body.replace("show_interest_person", str(current_login_user[0]))
            body = body.replace("phone", str(current_login_user[3]))
            body = body.replace("mail_id", str(current_login_user[2]))
            flash("your details have been shared to the seller.")
            send_email(seller_name[1], subject, body)
        conn.close()
        return render_template('seller_details.html', seller_detail=list(results), image_urls=image_urls)
    else:
        return redirect(url_for('login'))


@app.route('/sell', methods=['GET', 'POST'])
@login_required
def sell():
    global login_type
    if login_type:
        if request.method == 'POST':
            product_id = random.randint(1000, 9999)
            place_name = request.form['place_name']
            area = request.form['area']
            number_bedroom = request.form['number_bedroom']
            nearby_location = request.form['nearby_location']
            number_bathroom = request.form['number_bathroom']
            type_of_buildings = request.form.get('type_of_buildings')
            if 'file' not in request.files:
                return redirect(request.url)
            files = request.files.getlist('file')
            file_data_list = [None, None, None, None, None]
            for i in range(min(5, len(files))):
                if files[i] and files[i].filename != '':
                    file_data_list[i] = files[i].read()
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO rentify_details (area,places, bedrooms, bathroom, near_by, type_of_buildings, seller_id, product_id, 
                                            img_1, img_2, img_3, img_4, img_5) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,?)
            ''', (area, place_name, number_bedroom, number_bathroom, nearby_location, type_of_buildings,
                  current_login_id, product_id, *file_data_list))
            conn.commit()
            conn.close()
            return redirect(url_for('home'))
        return render_template('sell.html')
    else:
        return redirect(url_for('login'))


@app.route('/login', methods=['GET', 'POST'])
@login_required
def login():
    global current_date, current_time
    otp = ''
    if request.method == 'POST':
        email = request.form['email']
        create_otp = random.randint(100000, 999999)
        conn = sqlite3.connect(database)
        cursor = conn.cursor()
        fetch_name = cursor.execute('select first_name from login_details where email_id=?', (email,)).fetchone()
        cursor.execute(
            'update login_details set OTP=?,last_date_updated_otp=? ,last_tym_updated_otp=?  where email_id=?',
            (create_otp, current_date, current_time.strftime('%H:%M'), email))
        print(create_otp)
        flash("Please check your email")
        conn.commit()
        conn.close()
        subject = "Your One-Time Password (OTP) for Secure Access"
        body = otp_body.replace("User", fetch_name[0])
        body = body.replace("your_otp", str(create_otp))
        send_email(email, subject, body)
        return render_template('login.html', mail_id=email, otp=create_otp)
    return render_template('login.html', otp=otp)


@app.route('/otp_verify', methods=['GET', 'POST'])
@login_required
def otp_verify():
    global login_type, current_login_id
    if request.method == 'POST':
        otp = request.form['otp']
        email = request.form['email']
        conn = sqlite3.connect(database)
        cursor = conn.cursor()
        check_user_details = cursor.execute('select OTP,user_id, last_date_updated_otp, last_tym_updated_otp '
                                            'from login_details where email_id = ?', (email,)).fetchone()
        conn.close()
        given_datetime = datetime.combine(datetime.today(), dt_time(int(check_user_details[3].split(':')[0]),
                                                                    int(check_user_details[3].split(':')[1])))
        new_time = (given_datetime + timedelta(minutes=10)).time()
        if check_user_details[2] == str(current_date) and check_user_details[3] <= str(new_time) and int(otp) == int(
                check_user_details[0]):
            login_type = True
            start_time_counter()
            current_login_id = check_user_details[1]
            return redirect(url_for('home'))
        else:
            flash("Enter Correct OTP")
            return render_template('login.html', mail_id=email, otp=otp)
    return render_template('login.html')


@app.route('/sign_up', methods=['GET', 'POST'])
@login_required
def sign_up():
    if request.method == 'POST':
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        phone_number = request.form['phone_number']
        conn = sqlite3.connect(database)
        cursor = conn.cursor()
        check_user_details = cursor.execute('select email_id from login_details where email_id = ?',
                                            (email,)).fetchone()
        if check_user_details:
            flash("Account is already exist.")
        else:
            current_id = cursor.execute('select user_id from login_details').fetchall()
            if current_id:
                create_login_id = current_id[len(current_id) - 1][0] + 1
            else:
                create_login_id = 1000
            cursor.execute('''INSERT INTO login_details (first_name,last_name, email_id, phone_number, user_id)
                                   VALUES (?, ?, ?, ?, ?)''',
                           (first_name, last_name, email, phone_number, create_login_id))
            conn.commit()
            conn.close()
            subject = "Welcome to Rentify - Your Account Has Been Successfully Created"
            body = create_body.replace("User", first_name)
            send_email(email, subject, body)
            return redirect(url_for('login'))
        return render_template('sign_up.html', ft_name=first_name, lt_name=last_name, em_id=email,
                               ph_num=phone_number)
    return render_template('sign_up.html')


if __name__ == "__main__":
    app.run(debug=True)
