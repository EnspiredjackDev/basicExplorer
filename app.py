from flask import Flask, redirect, render_template_string, request
from bitcoin.rpc import RawProxy
import sqlite3
import threading
import time
from requests.exceptions import ConnectionError
import socket
from datetime import datetime, timezone

# Initialize Flask app
app = Flask(__name__)

# RPC connection details
rpc_user = 'user'
rpc_password = 'pass'
rpc_port = 33751 
rpc_host = '127.0.0.1'

# Coin settings
coinTicker = "NYAN"
coinName = "Nyancoin"
addressPrefixes = ["N"] # Include every address prefix, e.g. ["1", "3", "bc1"]

# Database settings
databaseLocation = "" # Leave empty to use the current directory

# Function to create the RPC connection
def create_rpc_connection():
    return RawProxy(service_port=rpc_port, btc_conf_file=None, service_url=f'http://{rpc_user}:{rpc_password}@{rpc_host}:{rpc_port}')

rpc_connection = create_rpc_connection()

# Function to initialize the database
def initialize_database():
    conn = sqlite3.connect(f'{databaseLocation}{coinName.lower()}_explorer.db')
    cursor = conn.cursor()

    # Create the table if it doesn't already exist
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS address_transactions (
        address TEXT,
        txid TEXT,
        value REAL,
        type TEXT,  -- 'received' or 'sent'
        block_height INTEGER
    )
    ''')

    conn.commit()
    conn.close()

# ensure the DB is ready
initialize_database()

index_html = '''
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{{coinName}} Blockchain Explorer</title>
  <style>
    body {
      background-color: #121212;
      color: #e0e0e0;
      font-family: Arial, sans-serif;
      margin: 0;
      padding: 0;
    }
    header, footer {
      background-color: #1f1f1f;
      padding: 10px;
      text-align: center;
    }
    a {
      color: #bb86fc;
      text-decoration: none;
    }
    a:hover {
      text-decoration: underline;
    }
    .container {
      padding: 20px;
    }
    .search-bar {
      margin-bottom: 20px;
      text-align: center;
    }
    input[type="text"] {
      padding: 10px;
      font-size: 16px;
      width: 300px;
      border-radius: 5px;
      border: none;
      margin-right: 10px;
    }
    button {
      background-color: #bb86fc;
      color: #121212;
      border: none;
      padding: 10px 20px;
      border-radius: 5px;
      cursor: pointer;
    }
    button:hover {
      background-color: #3700b3;
    }
    .block-card {
      padding: 20px;
      background-color: #1f1f1f;
      margin-bottom: 15px;
      border-radius: 8px;
      box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
    }
    .block-card h3 {
      margin-top: 0;
      margin-bottom: 10px;
      color: #bb86fc;
    }
    .block-info {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
      gap: 15px;
      margin-bottom: 10px;
    }
    .block-info strong {
      font-weight: 600;
    }
    .block-info p {
      margin: 0;
      font-size: 14px;
      word-wrap: break-word;
    }
    .pagination {
      margin: 20px 0;
      text-align: center;
    }
  </style>
</head>
<body>
  <header>
    <h1>{{ coinName }} Blockchain Explorer</h1>
  </header>
  <div class="container">

    <!-- Search Bar -->
    <div class="search-bar">
      <form action="/search" method="get">
        <input type="text" name="query" placeholder="Search by address, txid, or blockhash" required>
        <button type="submit">Search</button>
      </form>
    </div>

    <h2>Latest Blocks</h2>
    
    <!-- Block Cards -->
    <div class="block-list">
      {% for block in blocks %}
        <div class="block-card">
          <h3>Block Height: {{ block['height'] }}</h3>
          <div class="block-info">
            <div>
              <strong>Hash:</strong>
              <p><a href="/block?height={{ block['height'] }}">{{ block['hash'] }}</a></p>
            </div>
            <div>
              <strong>Time:</strong>
              <p>{{ block['time'] | timestamp_to_date }}</p>
            </div>
            <div>
              <strong>Time to Mine:</strong>
              <p>{{ block['time_to_mine'] }} seconds</p>
            </div>
            <div>
              <strong>Difficulty:</strong>
              <p>{{ block['difficulty'] }}</p>
            </div>
          </div>
          <div class="block-info">
            <div>
              <strong>Number of Transactions:</strong>
              <p>{{ block['num_tx'] }}</p>
            </div>
            <div>
              <strong>Size:</strong>
              <p>{{ block['size'] }} bytes</p>
            </div>
            <div>
              <strong>Total Value Transacted:</strong>
              <p>{{ block['total_value_transacted'] }} {{ coinTicker }}</p>
            </div>
          </div>
        </div>
      {% endfor %}
    </div>

    <!-- Pagination -->
    <div class="pagination">
      {% if prev_page %}
        <a href="/?page={{ prev_page }}"><button>Previous</button></a>
      {% endif %}
      {% if next_page %}
        <a href="/?page={{ next_page }}"><button>Next</button></a>
      {% endif %}
    </div>

    <h2>Recent Transactions</h2>
<div class="transaction-list">
  {% for tx in recent_transactions %}
    <div class="block-card">
      <h3>Transaction ID: <a href="/transaction?txid={{ tx.txid }}">{{ tx.txid }}</a></h3>
      <div class="block-info">
        <div>
          <strong>Time:</strong>
          <p>{{ tx.time }}</p>
        </div>
        <div>
          <strong>Value:</strong>
          <p>{{ tx.value }} {{ coinTicker }}</p>
        </div>
        <div>
          <strong>Size:</strong>
          <p>{{ tx.size }} bytes</p>
        </div>
        <div>
          <strong>Fee per Byte:</strong>
          <p>{{ tx.fee_per_byte }} {{ coinTicker }}/byte</p>
        </div>
        <div>
          <strong>Confirmations:</strong>
          <p>{{ tx.confirmations }}</p>
        </div>
        <div>
          <strong>Inputs / Outputs:</strong>
          <p>{{ tx.inputs }} / {{ tx.outputs }}</p>
        </div>
      </div>
    </div>
  {% endfor %}
</div>


<h2>Mempool Transactions</h2>
<div class="transaction-list">
  {% for tx in mempool_transactions %}
    <div class="block-card">
      <h3>Transaction ID: {{ tx.txid }}</h3>
      <div class="block-info">
        <div>
          <strong>Size:</strong>
          <p>{{ tx.size }} bytes</p>
        </div>
        <div>
          <strong>Fee per Byte:</strong>
          <p>{{ tx.fee_per_byte }} {{ coinTicker }}/byte</p>
        </div>
        <div>
          <strong>Value:</strong>
          <p>{{ tx.value }} {{ coinTicker }}</p>
        </div>
      </div>
    </div>
  {% endfor %}
</div>


  </div>
  <footer>
    <p>{{ coinName }} Blockchain Explorer</p>
  </footer>
</body>
</html>
'''

block_html = '''
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Block {{ block_height }}</title>
  <style>
    body {
      background-color: #121212;
      color: #e0e0e0;
      font-family: Arial, sans-serif;
      margin: 0;
      padding: 0;
    }
    header, footer {
      background-color: #1f1f1f;
      padding: 10px;
      text-align: center;
    }
    a {
      color: #bb86fc;
      text-decoration: none;
    }
    a:hover {
      text-decoration: underline;
    }
    .container {
      padding: 20px;
    }
    .section {
      margin-bottom: 20px;
    }
    .section h2 {
      border-bottom: 1px solid #444;
      padding-bottom: 10px;
      margin-bottom: 10px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
    }
    th, td {
      padding: 10px;
      text-align: left;
    }
    th {
      background-color: #1f1f1f;
    }
    td {
      background-color: #2a2a2a;
    }
    .back-button {
      display: inline-block;
      margin-top: 20px;
      padding: 10px 20px;
      background-color: #bb86fc;
      color: #121212;
      text-decoration: none;
      border-radius: 5px;
    }
    .back-button:hover {
      background-color: #3700b3;
    }
    .card {
      background-color: #1f1f1f;
      padding: 20px;
      border-radius: 8px;
      box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
      margin-bottom: 20px;
    }
    .card h3 {
      margin-top: 0;
    }
    .overview {
      background-color: #2a2a2a;
      padding: 15px;
      border-radius: 8px;
      margin-bottom: 20px;
    }
    .overview strong {
      font-weight: bold;
    }
    .two-column {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
    }
  </style>
</head>
<body>
  <header>
    <h1>Block {{ block_height }}</h1>
  </header>
  <div class="container">
    <!-- Two-Column Layout -->
    <div class="two-column">

      <!-- Block Overview Card -->
      <div class="card">
        <h3>Block Overview</h3>
        <div class="overview">
          <p><strong>Block Height:</strong> {{ block_height }}</p>
          <p><strong>Block Hash:</strong> {{ block.hash }}</p>
          <p><strong>Confirmations:</strong> {{ block.confirmations }}</p>
          <p><strong>Time:</strong> {{ block.time | timestamp_to_date }}</p>
          <p><strong>Time to Mine:</strong> {{ time_to_mine }} seconds</p>
          <p><strong>Total Value Transacted:</strong> {{ total_value_transacted }} {{ coinTicker }}</p>
        </div>
      </div>

      <!-- Block Details Card -->
      <div class="card">
        <h3>Block Details</h3>
        <div class="overview">
          <p><strong>Merkle Root:</strong> {{ block.merkleroot }}</p>
          <p><strong>Difficulty:</strong> {{ block.difficulty }}</p>
          <p><strong>Size:</strong> {{ block.size }} bytes</p>
          <p><strong>Previous Block Hash:<br></strong> <a href="/block?height={{ block_height - 1 }}">{{ block.previousblockhash }}</a></p>
          {% if block.nextblockhash %}
            <p><strong>Next Block Hash:<br></strong> <a href="/block?height={{ block_height + 1 }}">{{ block.nextblockhash }}</a></p>
          {% endif %}
        </div>
      </div>

    </div>

    <div class="section">
  <h2>Transactions in Block</h2>
  <table>
    <thead>
      <tr>
        <th>Transaction ID</th>
        <th>Amount</th>
        <th>Fees</th>
      </tr>
    </thead>
    <tbody>
      {% for tx in transactions %}
        <tr>
          <td><a href="/transaction?txid={{ tx.txid }}">{{ tx.txid }}</a></td>
          <td>
            {% if tx.is_coinbase %}
              <span style="color: #4caf50;">+{{ '%.8f' | format(tx.reward) }} {{ coinTicker }}</span>  <!-- Positive value for coinbase -->
            {% else %}
              {{ '%.8f' | format(tx.total_output) }} {{ coinTicker }}  <!-- Normal transaction output -->
            {% endif %}
          </td>
          <td>
            {% if tx.is_coinbase %}
              <span style="color: #4caf50;">+{{ '%.8f' | format(tx.tx_fee) }} {{ coinTicker }}</span>  <!-- Positive fee for coinbase -->
            {% else %}
              <span style="color: #f44336;">-{{ '%.8f' | format(tx.tx_fee) }} {{ coinTicker }}</span>  <!-- Negative fee for normal transactions -->
            {% endif %}
          </td>
        </tr>
      {% endfor %}
    </tbody>
  </table>
</div>


    <a class="back-button" href="/">Back to Home</a>
  </div>
  <footer>
    <p>{{ coinName }} Blockchain Explorer</p>
  </footer>
</body>
</html>
'''

transaction_html = '''
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Transaction {{ txid }}</title>
  <style>
    body {
      background-color: #121212;
      color: #e0e0e0;
      font-family: Arial, sans-serif;
      margin: 0;
      padding: 0;
    }
    header, footer {
      background-color: #1f1f1f;
      padding: 10px;
      text-align: center;
    }
    a {
      color: #bb86fc;
      text-decoration: none;
    }
    a:hover {
      text-decoration: underline;
    }
    .container {
      padding: 20px;
    }
    .section {
      margin-bottom: 20px;
    }
    .section h2 {
      border-bottom: 1px solid #444;
      padding-bottom: 10px;
      margin-bottom: 10px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
    }
    th, td {
      padding: 10px;
      text-align: left;
    }
    th {
      background-color: #1f1f1f;
    }
    td {
      background-color: #2a2a2a;
      word-wrap: break-word;  /* Ensures long text wraps */
    }
    .scriptsig-asm {
      font-size: 12px;  /* Smaller font size for ScriptSig */
      word-break: break-all;  /* Ensure it breaks on long lines */
    }
    .back-button {
      display: inline-block;
      margin-top: 20px;
      padding: 10px 20px;
      background-color: #bb86fc;
      color: #121212;
      text-decoration: none;
      border-radius: 5px;
    }
    .back-button:hover {
      background-color: #3700b3;
    }
    .card {
      background-color: #1f1f1f;
      padding: 20px;
      border-radius: 8px;
      box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
      margin-bottom: 20px;
    }
    .two-column {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 20px;
    }
    .overview {
      background-color: #2a2a2a;
      padding: 15px;
      border-radius: 8px;
      margin-bottom: 20px;
    }
  </style>
</head>
<body>
  <header>
    <h1>Transaction {{ txid }}</h1>
  </header>
  <div class="container">
    
    <!-- Two-Column Layout -->
    <div class="two-column">
      
      <!-- General Information Card -->
      <div class="card">
        <h3>General Information</h3>
        <div class="overview">
          <p><strong>Block Height:</strong> {{ block_height }}</p>
          <p><strong>Block Hash:</strong> <a href="/block?height={{ block_height }}"> {{ tx.blockhash }}</a></p>
          <p><strong>Confirmations:</strong> {{ tx.confirmations }}</p>
          <p><strong>Time:</strong> {{ time_formatted }}</p>
          <p><strong>Size:</strong> {{ tx.size }} bytes</p>
          <p><strong>Fee:</strong> {{ '%.8f' | format(total_fee) }} {{ coinTicker }}</p>
          <p><strong>Fee per Byte:</strong> {{ '%.8f' | format(fee_per_byte) }} {{ coinTicker }}/byte</p>
        </div>
      </div>

      <!-- Inputs / Outputs Summary Card -->
      <div class="card">
        <h3>Transaction Overview</h3>
        <div class="overview">
          <p><strong>Number of Inputs:</strong> {{ tx.vin|length }}</p>
          <p><strong>Number of Outputs:</strong> {{ tx.vout|length }}</p>
        </div>
      </div>

    </div>

    <!-- Inputs Section -->
    <div class="section">
      <h2>Inputs</h2>
      <table>
        <thead>
          <tr>
            <th>TXID</th>
            <th>VOUT</th>
            <th>Value</th>
            <th>Address</th>
            <th>ScriptSig (ASM)</th>
            <th>Sequence</th>
          </tr>
        </thead>
        <tbody>
          {% for vin in tx.vin %}
            {% if vin.type == 'coinbase' %}
              <tr>
                <td colspan="6">Coinbase Transaction: Mining Reward of {{ vin.value }} {{ coinTicker }}</td>
              </tr>
            {% else %}
              <tr>
                <td><a href="/transaction?txid={{ vin.txid }}">{{ vin.txid }}</a></td>
                <td>{{ vin.vout }}</td>
                <td>{{ vin.value }} {{ coinTicker }}</td>
                <td><a href="/address?address={{ vin.address }}">{{ vin.address }}</a></td>
                <td class="scriptsig-asm">{{ vin.scriptSig.asm }}</td>  <!-- Added class for ScriptSig -->
                <td>{{ vin.sequence }}</td>
              </tr>
            {% endif %}
          {% endfor %}
        </tbody>
      </table>
    </div>
    
    <!-- Outputs Section -->
    <div class="section">
      <h2>Outputs</h2>
      <table>
        <thead>
          <tr>
            <th>Value</th>
            <th>Address</th>
            <th>ScriptPubKey (ASM)</th>
          </tr>
        </thead>
        <tbody>
          {% for vout in tx.vout %}
            <tr>
              <td>{{ vout.value }} {{ coinTicker }}</td>
              <td>
                {% if vout.scriptPubKey.addresses %}
                  <a href="/address?address={{ vout.scriptPubKey.addresses[0] }}">{{ vout.scriptPubKey.addresses[0] }}</a>
                {% else %}
                  N/A
                {% endif %}
              </td>
              <td>{{ vout.scriptPubKey.asm }}</td>
            </tr>
          {% endfor %}
        </tbody>
      </table>
    </div>
    
    <a class="back-button" href="/">Back to Home</a>
  </div>
  <footer>
    <p>{{ coinName }} Blockchain Explorer</p>
  </footer>
</body>
</html>
'''

address_html = '''
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Address {{ address }}</title>
  <style>
    body {
      background-color: #121212;
      color: #e0e0e0;
      font-family: Arial, sans-serif;
      margin: 0;
      padding: 0;
    }
    header, footer {
      background-color: #1f1f1f;
      padding: 10px;
      text-align: center;
    }
    a {
      color: #bb86fc;
      text-decoration: none;
    }
    a:hover {
      text-decoration: underline;
    }
    .container {
      padding: 20px;
    }
    .section {
      margin-bottom: 20px;
    }
    .section h2 {
      border-bottom: 1px solid #444;
      padding-bottom: 10px;
      margin-bottom: 10px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
    }
    th, td {
      padding: 10px;
      text-align: left;
    }
    th {
      background-color: #1f1f1f;
    }
    td {
      background-color: #2a2a2a;
    }
    .back-button {
      display: inline-block;
      margin-top: 20px;
      padding: 10px 20px;
      background-color: #bb86fc;
      color: #121212;
      text-decoration: none;
      border-radius: 5px;
    }
    .back-button:hover {
      background-color: #3700b3;
    }
    .pagination {
  text-align: center;
  margin-top: 20px;
}

.button {
  background-color: #bb86fc;
  color: #121212;
  padding: 10px 20px;
  margin: 0 5px;
  border-radius: 5px;
  text-decoration: none;
  font-size: 16px;
  font-weight: bold;
  transition: background-color 0.3s;
  display: inline-block;
}

.button:hover {
  background-color: #3700b3;
  color: #ffffff;
}

  </style>
</head>
<body>
  <header>
    <h1>Address {{ address }}</h1>
  </header>
  <div class="container">
    <div class="section">
      <h2>Balance Information</h2>
      <p><strong>Received:</strong> {{ received_amount }} {{ coinTicker }}</p>
      <p><strong>Sent:</strong> {{ sent_amount }} {{ coinTicker }}</p>
      <p><strong>Balance:</strong> {{ balance }} {{ coinTicker }}</p>
    </div>
    
    <div class="section">
      <h2>Transactions</h2>
      <table>
        <thead>
          <tr>
            <th>Transaction ID</th>
            <th>Type</th>
            <th>Value</th>
            <th>Block Height</th>
          </tr>
        </thead>
        <tbody>
          {% for tx in transactions %}
            <tr>
              <td><a href="/transaction?txid={{ tx[0] }}">{{ tx[0] }}</a></td>
              <td>{{ tx[1] }}</td>
              <td>{{ tx[2] }} {{ coinTicker }}</td>
              <td>{{ tx[3] }}</td>
            </tr>
          {% else %}
            <tr><td colspan="4">No transactions found for this address.</td></tr>
          {% endfor %}
        </tbody>
      </table>
      <div class="pagination">
  {% if prev_page %}
    <a href="/address?address={{ address }}&page={{ prev_page }}" class="button">Previous</a>
  {% endif %}
  {% if next_page %}
    <a href="/address?address={{ address }}&page={{ next_page }}" class="button">Next</a>
  {% endif %}
</div>

    </div>
    
    <a class="back-button" href="/">Back to Home</a>
  </div>
  <footer>
    <p>{{ coinName }} Blockchain Explorer</p>
  </footer>
</body>
</html>
'''

not_found_html = '''
<!doctype html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Not Found</title>
  <style>
    body {
      background-color: #121212;
      color: #e0e0e0;
      font-family: Arial, sans-serif;
      margin: 0;
      padding: 0;
    }
    header, footer {
      background-color: #1f1f1f;
      padding: 10px;
      text-align: center;
    }
    .container {
      padding: 20px;
      text-align: center;
    }
    .back-button {
      display: inline-block;
      margin-top: 20px;
      padding: 10px 20px;
      background-color: #bb86fc;
      color: #121212;
      text-decoration: none;
      border-radius: 5px;
    }
    .back-button:hover {
      background-color: #3700b3;
    }
  </style>
</head>
<body>
  <header>
    <h1>{{ coinName }} Blockchain Explorer</h1>
  </header>
  <div class="container">
    <h2>Search Query Not Found</h2>
    <p>No results found for: {{ query }}</p>
    <a class="back-button" href="/">Back to Home</a>
  </div>
  <footer>
    <p>{{ coinName }} Blockchain Explorer</p>
  </footer>
</body>
</html>
'''

@app.route('/')
def index():
    # Get the current page number from the query parameters (for block pagination)
    page = int(request.args.get('page', 1))
    blocks_per_page = 10

    # Get the latest block height
    latest_block_height = rpc_connection.getblockcount()

    # Calculate the block range for pagination
    start_height = latest_block_height - (page - 1) * blocks_per_page
    end_height = max(0, start_height - blocks_per_page)

    blocks = []
    recent_transactions = []

    # Fetch block data for the current page (pagination)
    for height in range(start_height, end_height, -1):
        block_hash = rpc_connection.getblockhash(height)
        block = rpc_connection.getblock(block_hash)

        # Calculate time to mine the block (difference from the previous block)
        if height > 0:
            prev_block_hash = rpc_connection.getblockhash(height - 1)
            prev_block = rpc_connection.getblock(prev_block_hash)
            time_to_mine = block['time'] - prev_block['time']  # In seconds
        else:
            time_to_mine = 0  # No previous block for block 0

        # Calculate total value transacted in the block
        total_value_transacted = 0
        for txid in block['tx']:
            tx = rpc_connection.getrawtransaction(txid, True)
            for vout in tx['vout']:
                total_value_transacted += vout['value']

        # Append block data for rendering
        blocks.append({
            'height': height,
            'hash': block['hash'],
            'difficulty': block['difficulty'],
            'time': block['time'],
            'time_to_mine': time_to_mine,
            'num_tx': len(block['tx']),
            'size': block['size'],
            'total_value_transacted': total_value_transacted
        })

    # Set up pagination (for blocks)
    prev_page = page - 1 if start_height < latest_block_height else None
    next_page = page + 1 if end_height > 0 else None

    # Fetch recent transactions from the latest 5 blocks
    for height in range(latest_block_height, latest_block_height - 5, -1):
        block_hash = rpc_connection.getblockhash(height)
        block = rpc_connection.getblock(block_hash)

        # Collect transactions from the block
        for txid in block['tx']:
            tx = rpc_connection.getrawtransaction(txid, True)
            total_value = sum(vout['value'] for vout in tx['vout'])
            confirmations = tx['confirmations']
            size = tx['size']
            num_inputs = len(tx['vin'])
            num_outputs = len(tx['vout'])

            # Check if it's a coinbase transaction
            is_coinbase = 'coinbase' in tx['vin'][0]
            fee = 0
            fee_per_byte = 0

            if not is_coinbase:
                # Calculate fee and fee per byte
                total_input_value = 0
                for vin in tx['vin']:
                    if 'txid' in vin:  # Skip coinbase transactions
                        prev_tx = rpc_connection.getrawtransaction(vin['txid'], True)
                        prev_vout = prev_tx['vout'][vin['vout']]
                        total_input_value += prev_vout['value']
                fee = total_input_value - total_value
                fee_per_byte = fee / size if size > 0 else 0

            recent_transactions.append({
                'txid': txid,
                'time': datetime.fromtimestamp(tx['time'], timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC'),
                'value': total_value,
                'size': size,
                'confirmations': confirmations,
                'inputs': num_inputs,
                'outputs': num_outputs,
                'fee_per_byte': round(fee_per_byte, 8)
            })

    # Get mempool transactions (limit to first 10 for performance reasons)
    mempool_txids = rpc_connection.getrawmempool()
    mempool_transactions = []

    # Fetch more detailed information for each mempool transaction
    for txid in mempool_txids[:10]:  # Limit to the first 10
        tx = rpc_connection.getrawtransaction(txid, True)
        total_value = sum(vout['value'] for vout in tx['vout'])
        size = tx['size']
        
        # Calculate fee and fee per byte for mempool transactions
        total_input_value = 0
        for vin in tx['vin']:
            prev_tx = rpc_connection.getrawtransaction(vin['txid'], True)
            prev_vout = prev_tx['vout'][vin['vout']]
            total_input_value += prev_vout['value']
        fee = total_input_value - total_value
        fee_per_byte = fee / size if size > 0 else 0

        mempool_transactions.append({
            'txid': txid,
            'size': tx['size'],  # Transaction size
            'value': total_value,  # Total value of the transaction
            'fee_per_byte': round(fee_per_byte, 8)  # Fee per byte
        })

    # Render the main page with blocks, recent transactions, and mempool transactions
    return render_template_string(index_html, 
                                  blocks=blocks, 
                                  prev_page=prev_page, 
                                  next_page=next_page, 
                                  recent_transactions=recent_transactions, 
                                  mempool_transactions=mempool_transactions,
                                  coinName=coinName,
                                  coinTicker=coinTicker)

@app.route('/block')
def block():
    try:
        height = int(request.args.get('height'))
        block_hash = rpc_connection.getblockhash(height)
        block = rpc_connection.getblock(block_hash)
        
        # Get previous block for time to mine calculation
        if height > 0:
            prev_block_hash = rpc_connection.getblockhash(height - 1)
            prev_block = rpc_connection.getblock(prev_block_hash)
            time_to_mine = block['time'] - prev_block['time']  # In seconds
        else:
            time_to_mine = 0  # No previous block for block 0
        
        total_value_transacted = 0
        transactions = []
        total_fees = 0  # To accumulate all non-coinbase fees

        for txid in block['tx']:
            tx = rpc_connection.getrawtransaction(txid, True)

            total_output_value = sum(vout['value'] for vout in tx['vout'])
            if 'coinbase' in tx['vin'][0]:  # Check if it's a coinbase transaction
                is_coinbase = True
                tx_fee = 0  # No fee for coinbase transaction
                reward = total_output_value  # Reward equals the output value
            else:
                is_coinbase = False
                # Calculate the total input value for non-coinbase transactions
                total_input_value = 0
                for vin in tx['vin']:
                    prev_tx = rpc_connection.getrawtransaction(vin['txid'], True)
                    total_input_value += prev_tx['vout'][vin['vout']]['value']
                
                tx_fee = total_input_value - total_output_value  # Transaction fee
                total_fees += tx_fee  # Add to total fees for the block
                reward = 0  # No reward for non-coinbase transactions
            
            transactions.append({
                'txid': txid,
                'total_output': total_output_value,
                'tx_fee': tx_fee,
                'reward': reward,
                'is_coinbase': is_coinbase,
            })
            
            total_value_transacted += total_output_value

        # Add total_fees to the coinbase transaction's reward
        for tx in transactions:
            if tx['is_coinbase']:
                tx['tx_fee'] = total_fees  # Assign all fees to the coinbase transaction

        num_transactions = len(block['tx'])

        return render_template_string(block_html, 
                                      block=block, 
                                      block_height=height, 
                                      num_transactions=num_transactions,
                                      time_to_mine=time_to_mine,
                                      total_value_transacted=total_value_transacted,
                                      transactions=transactions,
                                      coinName=coinName,
                                      coinTicker=coinTicker)
    except (ValueError, Exception) as e:
        return f"Error: {e}", 400

@app.route('/transaction')
def transaction():
    try:
        txid = request.args.get('txid')
        tx = rpc_connection.getrawtransaction(txid, True)

        # Fetch the block height using the block hash
        block = rpc_connection.getblock(tx['blockhash'])
        block_height = block['height']

        # Fetch the value for each input (vin), handling coinbase transactions
        total_input_value = 0
        for vin in tx['vin']:
            if 'coinbase' in vin:
                vin['type'] = 'coinbase'
                vin['value'] = tx['vout'][0]['value']  # Reward value
                vin['address'] = 'N/A'  # Coinbase doesn't have an address
            else:
                # Fetch the previous transaction to get the vout value and address
                prev_tx = rpc_connection.getrawtransaction(vin['txid'], True)
                prev_vout = prev_tx['vout'][vin['vout']]
                vin['value'] = prev_vout['value']
                vin['address'] = prev_vout['scriptPubKey']['addresses'][0] if 'addresses' in prev_vout['scriptPubKey'] else 'N/A'
                total_input_value += vin['value']  # Calculate total input value

        # Calculate total output value
        total_output_value = sum(vout['value'] for vout in tx['vout'])

        # Calculate the total fee
        total_fee = total_input_value - total_output_value if total_input_value else 0
        fee_per_byte = total_fee / tx['size'] if tx['size'] > 0 else 0

        # Format time in human-readable format
        time_formatted = datetime.fromtimestamp(tx['time'], timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')

        return render_template_string(transaction_html, 
                                      tx=tx, 
                                      txid=txid, 
                                      block_height=block_height,
                                      total_fee=total_fee, 
                                      fee_per_byte=fee_per_byte, 
                                      time_formatted=time_formatted,
                                      coinName=coinName,
                                      coinTicker=coinTicker)
    except Exception as e:
        return f"Error: {e}", 400
    
@app.route('/address')
def address():
    try:
        address = request.args.get('address')
        page = int(request.args.get('page', 1))  # Get the page number from the query parameters
        transactions_per_page = 20  # Set the number of transactions per page

        # Connect to SQLite database
        conn = sqlite3.connect(f'{databaseLocation}{coinName.lower()}_explorer.db')
        cursor = conn.cursor()

        # Query received and sent amounts
        cursor.execute('''
            SELECT SUM(value) FROM address_transactions WHERE address = ? AND type = 'received'
        ''', (address,))
        received_amount = cursor.fetchone()[0] or 0

        cursor.execute('''
            SELECT SUM(value) FROM address_transactions WHERE address = ? AND type = 'sent'
        ''', (address,))
        sent_amount = cursor.fetchone()[0] or 0

        balance = received_amount - sent_amount

        # Calculate the offset for pagination
        offset = (page - 1) * transactions_per_page

        # Query transactions with pagination
        cursor.execute('''
            SELECT txid, type, SUM(value), block_height
            FROM address_transactions
            WHERE address = ?
            GROUP BY txid, type, block_height
            ORDER BY block_height DESC
            LIMIT ? OFFSET ?
        ''', (address, transactions_per_page, offset))

        transactions = cursor.fetchall()

        # Query the total number of transactions for pagination controls
        cursor.execute('''
            SELECT COUNT(DISTINCT txid) FROM address_transactions WHERE address = ?
        ''', (address,))
        total_transactions = cursor.fetchone()[0]

        # Calculate total number of pages
        total_pages = (total_transactions + transactions_per_page - 1) // transactions_per_page

        # Determine if "Previous" and "Next" buttons should be shown
        prev_page = page - 1 if page > 1 else None
        next_page = page + 1 if page < total_pages else None

        return render_template_string(address_html,
                                      address=address,
                                      transactions=transactions,
                                      received_amount=received_amount,
                                      sent_amount=sent_amount,
                                      balance=balance,
                                      prev_page=prev_page,
                                      next_page=next_page,
                                      coinName=coinName,
                                      coinTicker=coinTicker)
    except Exception as e:
        return f"Error: {e}", 400
    
@app.route('/search')
def search():
    query = request.args.get('query', '').strip()

    # 1. Check if query matches a block hash
    try:
        block = rpc_connection.getblock(query)
        return redirect(f'/block?height={block["height"]}')
    except Exception:
        pass

    # 2. Check if query matches a transaction hash
    try:
        tx = rpc_connection.getrawtransaction(query, True)
        return redirect(f'/transaction?txid={query}')
    except Exception:
        pass

    # 3. Check if query matches an address (We'll just redirect to the address page)
    try:
        # You could add more sophisticated validation for address format here
        if len(query) > 0:
          if any(query.startswith(prefix) for prefix in addressPrefixes):
            return redirect(f'/address?address={query}')
    except Exception:
        pass

    # If none of the checks worked, show a Not Found page
    return render_template_string(not_found_html, query=query)

# Function to parse blocks and update the database
def parse_blocks():
    retries = 3  # Number of retries before failing
    delay = 5    # Delay between retries in seconds
    global rpc_connection  # Ensure we use the latest connection object
    try:
        conn = sqlite3.connect(f'{databaseLocation}{coinName.lower()}_explorer.db')
        cursor = conn.cursor()

        latest_block_height = rpc_connection.getblockcount()

        # Get the last block height we parsed
        cursor.execute('SELECT MAX(block_height) FROM address_transactions')
        last_parsed_height = cursor.fetchone()[0] or 0
        print("last process height: " + str(last_parsed_height))

        # Parse new blocks since the last parsed height
        for height in range(last_parsed_height + 1, latest_block_height + 1):
            block_hash = rpc_connection.getblockhash(height)
            block = rpc_connection.getblock(block_hash)

            for txid in block['tx']:
                tx = rpc_connection.getrawtransaction(txid, True)

                # Store received values in the database
                for vout in tx['vout']:
                    if 'addresses' in vout['scriptPubKey']:
                        for address in vout['scriptPubKey']['addresses']:
                            value_float = float(vout['value'])  # Convert Decimal to float
                            cursor.execute('''
                                INSERT INTO address_transactions (address, txid, value, type, block_height)
                                VALUES (?, ?, ?, ?, ?)
                            ''', (address, txid, value_float, 'received', height))

                # Store sent values in the database (inputs)
                for vin in tx['vin']:
                    if 'txid' in vin:
                        prev_tx = rpc_connection.getrawtransaction(vin['txid'], True)
                        prev_vout = prev_tx['vout'][vin['vout']]
                        if 'addresses' in prev_vout['scriptPubKey']:
                            for address in prev_vout['scriptPubKey']['addresses']:
                                value_float = float(prev_vout['value'])  # Convert Decimal to float
                                cursor.execute('''
                                    INSERT INTO address_transactions (address, txid, value, type, block_height)
                                    VALUES (?, ?, ?, ?, ?)
                                ''', (address, txid, value_float, 'sent', height))
            print("processed block: " + block_hash)
            conn.commit()

        conn.close()

    except (ConnectionError, socket.error, socket.timeout) as e:
        retries -= 1
        print(f"Error parsing blocks: {e}. Retrying in {delay} seconds...")
        time.sleep(delay)
        if retries > 0:
            parse_blocks()  # Retry parsing blocks
        else:
            print("Max retries reached. Could not connect.")
            # Reconnect the RPC connection
            rpc_connection = create_rpc_connection()

    except Exception as e:
        print(f"Error parsing blocks: {e}")

# Function to run parse_blocks periodically
def run_periodic_block_parsing():
    while True:
        parse_blocks()
        time.sleep(10)  # Run every 10 seconds

# Start the background thread for periodic block parsing
threading.Thread(target=run_periodic_block_parsing, daemon=True).start()

@app.template_filter('timestamp_to_date')
def timestamp_to_date_filter(timestamp):
    return datetime.fromtimestamp(timestamp, timezone.utc).strftime('%Y-%m-%d %H:%M:%S UTC')

if __name__ == '__main__':
    app.run(debug=True)
