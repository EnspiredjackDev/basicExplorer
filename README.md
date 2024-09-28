
# Blockchain Explorer for Bitcoin Forks

A Flask-based blockchain explorer compatible with any Bitcoin fork. This web application allows you to explore blocks, transactions, and addresses on the blockchain of your chosen cryptocurrency.

## Table of Contents

- [Features](#features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
- [Setting Up Your Node](#setting-up-your-node)
- [Running the Application](#running-the-application)
- [Usage](#usage)
- [Notes](#notes)
- [License](#license)

## Features

- **Latest Blocks**: View detailed information about the most recent blocks.
- **Block Details**: Explore individual blocks, including transactions and metadata.
- **Transaction Details**: Inspect transaction inputs, outputs, fees, and more.
- **Address Lookup**: Check address balances and transaction histories.
- **Search Functionality**: Search for blocks, transactions, or addresses.
- **Mempool Transactions**: View unconfirmed transactions in the mempool.
- **Pagination**: Navigate through blocks and address transactions with ease.
- **Dark Mode UI**: Enjoy a sleek, dark-themed user interface.

## Prerequisites

- **Python 3.x**
- **pip** (Python package manager)
- **Flask** and other required Python packages (specified in `requirements.txt`)
- **SQLite3** (for the local database)
- **Full Node of Your Coin**: A fully synchronized node of your Bitcoin fork with RPC enabled.
- **Basic Knowledge**: Familiarity with running a blockchain node and configuring RPC settings.

## Installation

1. **Clone the Repository**

   ```bash
   git clone https://github.com/EnspiredjackDev/basicExplorer
   cd basicExplorer
   ```

2. **Install Python Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

3. **Verify Node Synchronization**

   Make sure your coin's full node is running and fully synchronized with the network.

## Configuration

Before running the application, you need to configure it to connect to your node and set up coin-specific settings.

### 1. RPC Connection Details

Edit the RPC connection details in the script (`app.py`):

```python
# RPC connection details
rpc_user = 'user'          # Your RPC username
rpc_password = 'pass'      # Your RPC password
rpc_port = 8332            # RPC port (default is 8332 for Bitcoin)
rpc_host = '127.0.0.1'     # RPC host (usually localhost)
```

Ensure these match the RPC settings in your node's configuration file (e.g., `bitcoin.conf`).

### 2. Coin Settings

Set the coin-specific information:

```python
# Coin settings
coinTicker = "BTC"         # Ticker symbol of your coin (e.g., BTC)
coinName = "Bitcoin"       # Full name of your coin (e.g., Bitcoin)
addressPrefixes  = ["1", "3", "bc1"] # Full list of every address prefix
```

### 3. Database Settings

Specify the location for the SQLite database:

```python
# Database settings
databaseLocation = ""      # Leave empty to use the current directory
```

By default, the database file will be created in the same directory as the script. You can specify a different path if desired.

## Setting Up Your Node

To use this explorer, you need to run a full node of your Bitcoin fork with RPC enabled.

### 1. Install the Full Node Software

Download and install the full node software for your coin. This typically involves:

- Downloading the binary or compiling from source.
- Following the coin's official documentation for installation instructions.

### 2. Configure the Node

Edit the node's configuration file (commonly named `coinname.conf`, but it may vary) to enable RPC and set the necessary parameters.

Example `bitcoin.conf`:

```
server=1
daemon=1
rpcuser=user
rpcpassword=pass
rpcallowip=127.0.0.1
rpcport=8332
txindex=1
```

**Important Settings:**

- `server=1`: Enables RPC server.
- `daemon=1`: Runs the node in the background as a daemon.
- `rpcuser` and `rpcpassword`: Set these to match the RPC details in the script.
- `rpcallowip`: IP addresses allowed to connect (use `127.0.0.1` for local connections).
- `rpcport`: The RPC port (default is `8332` for Bitcoin).
- `txindex=1`: Enables transaction indexing, which is necessary for some RPC calls used by the explorer.

#### Default `bitcoin.conf` Locations:

- **Linux**: `~/.bitcoin/bitcoin.conf`
- **Windows**: `C:\Users\YourUsername\AppData\Roaming\Bitcoin\bitcoin.conf`
- **macOS**: `~/Library/Application Support/Bitcoin/bitcoin.conf`

**This will differ based on your coin, make sure to change bitcoin to your coin name**

### 3. Start the Node

Run your node and wait for it to fully synchronize with the network. This may take some time depending on the blockchain size.

If you're using a custom path, you can specify it manually when starting your node:

```bash
./yourcoind -conf=/path/to/your/bitcoin.conf
```

Replace `yourcoind` with the name of your coin's daemon.

You can also use the QT versions if you prefer.

### 4. Verify RPC Connection


Once your node is running, you can verify the RPC connection using `curl`. Here's an example command to check your node's blockchain information:

```bash
curl --user user:pass --data-binary '{"jsonrpc":"1.0","id":"curltext","method":"getblockchaininfo","params":[]}' -H 'content-type:text/plain;' http://127.0.0.1:8332/
```

Replace `user` and `pass` with your actual RPC credentials and set `127.0.0.1:8332` to the correct ip:port for your coin. If everything is set up correctly, you should receive a JSON response with details about the blockchain.

## Running the Application

Start the Flask application by running the script:

```bash
python3 app.py
```

By default, the app runs in debug mode on `http://127.0.0.1:5000`. You can access it through your web browser.

### Running in Production*

For production use, consider using a production-grade WSGI server like Gunicorn and a reverse proxy like Nginx.

Example with Gunicorn:

```bash
gunicorn app:app
```
\* It's up to you if you feel like you want to run this in a production environment, however it has not been tested for such use.

## Usage

Open your web browser and navigate to:

```
http://127.0.0.1:5000
```

## Notes

- **Synchronization**: Ensure that your node is fully synchronized before using the explorer to get accurate data.
- **Database**: The explorer uses an SQLite database to store address transactions & requires syncing. This may take a while on first run.
- **Background Parsing**: The application includes a background thread that periodically parses new blocks and updates the database.

### Handling Large Blockchains

For blockchains with a large number of transactions, consider the following:

- **Increase Parsing Interval**: Adjust the `time.sleep(10)` in `run_periodic_block_parsing()` to parse blocks less frequently.

## License

This project is open-source and available under the MIT License.

---

**Disclaimer**: This explorer is provided as-is and may require adjustments to work with specific Bitcoin forks, especially those with significant differences from Bitcoin Core.


# Additional Information

## Security Considerations

- **RPC Security**: Be cautious with RPC settings. Do not expose RPC ports to untrusted networks.
- **Credentials**: Keep your RPC username and password secure.

## Troubleshooting

- **Connection Issues**: If the app cannot connect to the RPC server, verify that the node is running and RPC settings are correct.
- **Database Errors**: Ensure that the SQLite database file is accessible and not corrupted.
- **Synchronization Delays**: If data appears outdated, check that the background parsing thread is running without errors.

## Acknowledgments

This explorer is inspired by blockchain explorers like Blockchain.info and Blockchair, aiming to provide an accessible way to explore blockchain data for any Bitcoin fork with a special thanks to Nyan/Katkoyn for their [explorer](https://web.archive.org/web/20240526220829/https://explorer.katkoyn.com/ex.koyn) as it helped with some design.

**This readme was made with help of ChatGPT**