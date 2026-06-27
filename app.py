from flask import Flask, render_template, request, redirect, session, flash
import mysql.connector
from datetime import datetime, timedelta

app = Flask(__name__)
app.secret_key = 'al_ghaznavi_secure_secret_key_matrix'

def get_db_connection():
    """Handles centralized connection sequences for MySQL database server architecture"""
    try:
        conn = mysql.connector.connect(
            host='localhost',
            user='root',
            password='F24-1009',  # Adjust this if a local root password is configuration dependent
            database='al_ghaznavi_library'
        )
        return conn
    except mysql.connector.Error:
        return None

@app.route('/')
def home():
    if session.get('user_id'):
        if session.get('role') == 'admin':
            return redirect('/admin')
        return redirect('/dashboard')
    return render_template('index.html')

@app.route('/login', methods=['POST'])
def login():
    email = request.form.get('email')
    password = request.form.get('password')
    
    conn = get_db_connection()
    if conn is None:
        flash("Database server is offline. Please start MySQL.", "danger")
        return redirect('/')
        
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT * FROM users WHERE email = %s AND password = %s", (email, password))
    user = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    if user:
        session['user_id'] = user['user_id']
        session['name'] = user['name']
        session['role'] = user['role']
        flash(f"Logged in successfully as {user['name']}.", "success")
        return redirect('/')
    else:
        flash("Invalid identification credentials. Please try again.", "danger")
        return redirect('/')

@app.route('/dashboard')
def dashboard():
    if not session.get('user_id') or session.get('role') != 'student':
        return redirect('/')
        
    search_query = request.args.get('search', '')
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    if search_query:
        query = "SELECT * FROM books WHERE title LIKE %s OR author LIKE %s OR genre LIKE %s"
        cursor.execute(query, (f"%{search_query}%", f"%{search_query}%", f"%{search_query}%"))
    else:
        cursor.execute("SELECT * FROM books")
    books = cursor.fetchall()
    
    cursor.execute("""
        SELECT t.transaction_id, b.title, t.due_date 
        FROM transactions t 
        JOIN books b ON t.book_id = b.book_id 
        WHERE t.user_id = %s AND t.status = 'borrowed'
    """, (session['user_id'],))
    checkouts = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return render_template('dashboard.html', books=books, checkouts=checkouts, search_query=search_query)

@app.route('/borrow/<int:book_id>', methods=['POST'])
def borrow_book(book_id):
    if not session.get('user_id') or session.get('role') != 'student':
        return redirect('/')
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT available_copies FROM books WHERE book_id = %s", (book_id,))
    book = cursor.fetchone()
    
    if book and book['available_copies'] > 0:
        borrow_date = datetime.now().date()
        due_date = borrow_date + timedelta(days=14)
        
        cursor.execute(
            "INSERT INTO transactions (user_id, book_id, borrow_date, due_date, status) VALUES (%s, %s, %s, %s, 'borrowed')",
            (session['user_id'], book_id, borrow_date, due_date)
        )
        cursor.execute("UPDATE books SET available_copies = available_copies - 1 WHERE book_id = %s", (book_id,))
        conn.commit()
        flash("Volume allocated successfully. Due date configured for 14 days.", "success")
    else:
        flash("Operational Error: Volume holds no available shelf copies.", "danger")
        
    cursor.close()
    conn.close()
    return redirect('/dashboard')

@app.route('/return/<int:transaction_id>', methods=['POST'])
def return_book(transaction_id):
    if not session.get('user_id'):
        return redirect('/')
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT book_id FROM transactions WHERE transaction_id = %s", (transaction_id,))
    record = cursor.fetchone()
    
    if record:
        return_date = datetime.now().date()
        cursor.execute(
            "UPDATE transactions SET return_date = %s, status = 'returned' WHERE transaction_id = %s",
            (return_date, transaction_id)
        )
        cursor.execute("UPDATE books SET available_copies = available_copies + 1 WHERE book_id = %s", (record['book_id'],))
        conn.commit()
        flash("Return processed successfully. Inventory array incremented.", "success")
        
    cursor.close()
    conn.close()
    return redirect('/')

@app.route('/admin')
def admin_panel():
    if not session.get('user_id') or session.get('role') != 'admin':
        return redirect('/')
        
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT t.transaction_id, u.name as user_name, u.email, b.title, t.borrow_date, t.due_date, t.status 
        FROM transactions t
        JOIN users u ON t.user_id = u.user_id
        JOIN books b ON t.book_id = b.book_id
        ORDER BY t.transaction_id DESC
    """)
    global_transactions = cursor.fetchall()
    
    cursor.close()
    conn.close()
    return render_template('admin.html', global_transactions=global_transactions)

@app.route('/admin/add-book', methods=['POST'])
def add_book():
    if not session.get('user_id') or session.get('role') != 'admin':
        return redirect('/')
        
    title = request.form.get('title')
    author = request.form.get('author')
    isbn = request.form.get('isbn')
    genre = request.form.get('genre')
    total_copies = int(request.form.get('total_copies', 1))
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute(
            "INSERT INTO books (isbn, title, author, genre, total_copies, available_copies) VALUES (%s, %s, %s, %s, %s, %s)",
            (isbn, title, author, genre, total_copies, total_copies)
        )
        conn.commit()
        flash("New inventory structure inserted into system catalog.", "success")
    except mysql.connector.Error as err:
        flash(f"Database conflict: {err.msg}", "danger")
        
    cursor.close()
    conn.close()
    return redirect('/admin')

@app.route('/logout')
def logout():
    session.clear()
    flash("Session context terminated successfully.", "info")
    return redirect('/')

if __name__ == '__main__':
    app.run(debug=True)