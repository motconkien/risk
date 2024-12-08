from tkinter import * 
from tkinter.ttk import * 
from tkinter import ttk
from mysql.connector import connect
import pandas as pd 
import numpy as np
import tkinter.simpledialog as simpledialog
from helpers import TreeviewEdit

#calculate functions



#query form database
query = '''select * from price'''

query_2 = '''
    SELECT 
 o.account,
    o.orderticket,
    o.opentime,
    o.side,
    (if(o.side = "sell",-1,1)*100000*o.size) as vol,
    substring(o.symbol,1,6) as symbol,
    o.openprice,
    o.currentprice,
    (o.comm + o.swap + o.floatpl) as floatpl,
    (o.size * o.openprice * 100000) as capital,
    CASE 
        WHEN SUBSTRING(o.symbol, 4, 3) = "USD" THEN 
            (o.comm + o.swap) -- If the base currency is USD, fee is not adjusted
        WHEN EXISTS (
            SELECT 1 
            FROM price p 
            WHERE p.symbol = CONCAT(SUBSTRING(o.symbol, 4, 3), "USD") AND o.account = p.account
        ) THEN 
            (o.comm + o.swap) / 
            (SELECT (p.bid + p.ask) / 2 
             FROM price p 
             WHERE p.symbol = CONCAT(SUBSTRING(o.symbol, 4, 3), "USD") AND o.account = p.account)
        WHEN EXISTS (
            SELECT 1 
            FROM price p 
            WHERE p.symbol = CONCAT("USD", SUBSTRING(o.symbol, 4, 3)) AND o.account = p.account
        ) THEN 
            (o.comm + o.swap) * 
            (SELECT (p.bid + p.ask) / 2 
             FROM price p 
             WHERE p.symbol = CONCAT("USD", SUBSTRING(o.symbol, 4, 3)) AND o.account = p.account)
        ELSE NULL -- If no matching price data, fee is NULL
    END AS adjusted_fee,
    o.date
FROM 
    positions o;

'''

query_3 = '''WITH temp AS (
    SELECT 
        account,
        DATE(date) AS day,
        MAX(date) AS max_datetime
    FROM 
        account
    GROUP BY 
        account, DATE(date)
),
limited_days AS (
    SELECT DISTINCT day
    FROM temp
    ORDER BY day DESC
    LIMIT 2
),
filtered_temp AS (
    SELECT *
    FROM temp
    WHERE day IN (SELECT day FROM limited_days)
)
SELECT *
FROM account
WHERE (account, date) IN (
    SELECT account, max_datetime
    FROM filtered_temp
);'''

#calculation
def fetch_data(query):
    host = '127.0.0.1'
    user = 'root'
    password = 'huyen20897'
    port = '3306'
    db = 'test'
    try:
        conn = connect(host = host, user = user, password = password, port = port, database = db)
        if conn.is_connected():
            print('Connected successfully')
         
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        conn.close()
        return rows

    except Exception as e:
        print(f'Error: {e}')

    finally:
        if 'conn' in locals() and conn.is_connected():
            conn.close()

def create_table(parent, query, columns):
    data = fetch_data(query)
    tree = ttk.Treeview(parent, columns= columns)

    for i in range(len(columns)):
        tree.heading(f'#{i+1}',text = columns[i])
        max_length = max(len(str(item[i])) for item in data)
        tree.column(f'#{i+1}',width = max(100, max_length * 10),stretch=True)

    for index,row in enumerate(data):
        if index % 2 == 0:
            tree.insert('','end',text=index, values = row,tags=('Row1',))
        else:
            tree.insert('','end',text=index, values = row,tags=('Row2',))
    
    tree.pack(fill = 'both', expand=True)
    return tree

def create_hierarchical_table(parent):
    '''Create a hierarchical table to display the open positions of each account.'''
    data = fetch_data(query_2)
    days = ["Today", "1", "2", "3", "4", "5", "6", "7", "8", "9"]

    # Define columns
    columns = ["Symbol", "Size", "Days", "Input", "Current Price", "Float PL", "Different", "Cover Lots"]
    tree = TreeviewEdit(parent, columns=columns, show='tree headings')

    # Configure the tree column
    tree.heading("#0", text="Account")
    tree.column("#0", width=150, stretch=True)

    # Configure other columns
    for i, col in enumerate(columns):
        tree.heading(f'#{i+1}', text=col)
        tree.column(f'#{i+1}', width=100, stretch=True)
    
    # Process data into DataFrame
    cols = ['account', 'orderticket', 'opentime', 'side', 'size', 'symbol', 'openprice', 'currentprice', 
            'floatpl', 'capital', 'adjusted_fee', 'date']
    df = pd.DataFrame(data, columns=cols)
    df['date'] = pd.to_datetime(df['date'])

    # Filter for maximum day data
    max_day = df.groupby(['account', 'symbol'])['date'].max().reset_index()
    max_day.columns = ['account', 'symbol', 'max_day']
    df = pd.merge(df, max_day, on=['account', 'symbol'])
    df_filtered = df[df['date'] == df['max_day']]

    # Group and compute necessary metrics
    result = df_filtered.groupby(['account', 'symbol'])[['size', 'floatpl', 'capital', 'adjusted_fee']].sum().reset_index()
    result['vwap'] = (result['capital'] + result['adjusted_fee']) / result['size']
    result = pd.merge(result, df_filtered.groupby(['symbol'])['currentprice'].max().reset_index(), on='symbol')

    #parent rows insert
    parent_set = set(result['account'])
    parent_dict = {}
    symbol_dict = {}

    # Iterate over the set
    for account in parent_set:
        parent_dict[account] = tree.insert('', 'end', text=account)

    print(parent_dict)
    #insert the child rows
    for _,row in result.iterrows():
        account = row['account']
        symbol = row['symbol']
        size = row['size']
        current_price = row['currentprice']
        floatpl = row['floatpl']

        # Add account as a parent row if not already added
        if account not in parent_dict:
            parent_dict[account] = tree.insert('', 'end', text=account)

        # Add symbol row if not already added
        if (account, symbol) not in symbol_dict:
            symbol_dict[(account, symbol)] = tree.insert(
                parent_dict[account], 'end', values=(symbol, '', '', '', '', '', '', '')
            )

        # Add days as child rows under the symbol
        for day in days:
            tree.insert(
                symbol_dict[(account, symbol)], 'end',
                values=('', size, day, '', current_price, floatpl, '', '')
            )


    tree.pack(fill='both',expand = True)

    return tree


def update_table(tree,fetch_function, query):
    new_data = fetch_function(query)
    for row in tree.get_children():
        tree.delete(row)
    
    #insert new data
    for index,row in enumerate(new_data):
        tree.insert('','end',text=index, values = row)




#UI set up
root = Tk()
root.title("Test")

style = ttk.Style()

# Configure the Treeview widget style
style.configure("Treeview",
                font=("Arial", 12),  # Font and size for rows
                rowheight=30,        # Row height
                borderwidth=1,       # Border width
                relief="solid"    # Solid border
                )# Background color for Treeview

# Configure the header style
style.configure("Treeview.Heading",
                font=("Arial", 14),  # Font and size for the header
                rowheight=40,        # Row height for header
                relief="solid",      # Border for header
                anchor="center")     # Center the header text

# Configure alternating row colors
style.configure("Treeview.Row1", background="#e0e0e0", fieldbackground="#e0e0e0")  # Light row color
style.configure("Treeview.Row2", background="#d0d0d0", fieldbackground="#d0d0d0")  # Dark row color

#menubar setup
menubar = Menu(root)
root.config(menu=menubar)

#tabs setup
tab_control = Notebook(root)

#create different frame
price_frame = Frame(tab_control)
position_frame = Frame(tab_control)
account_frame = Frame(tab_control)
others_frame = Frame(tab_control)

tab_control.add(price_frame, text = 'Current price')
tab_control.add(position_frame, text = 'Positions')
tab_control.add(account_frame, text = 'Account')
tab_control.add(others_frame, text='Others')


price_columns = ['account','symbol','bid','ask','date']
postions_columns = ['account','orderticket','opentime','side','size','symbol','openprice','currentprice','floatpl','capitall','adjusted_fee','date']
account_columns = ['account','balance','equity','margin','credit','floatpl','closepl','date']
price_tree = create_table(price_frame,query,price_columns)
position_tree = create_table(position_frame,query_2,postions_columns)
account_tree = create_table(account_frame,query_3, account_columns)
others_tree = create_hierarchical_table(others_frame)


#refresh function 
def refresh_price():
    update_table(price_tree,fetch_data,query)
    root.after(2000,refresh_price)

def refresh_positions():
    update_table(position_tree,fetch_data,query_2)
    root.after(2000,refresh_positions)

def refresh_account():
    update_table(account_tree,fetch_data,query_3)
    root.after(2000,refresh_account)

tab_control.pack(expand=1, fill='both')

refresh_price()
refresh_positions()
refresh_account()

root.resizable(True, True)



mainloop()