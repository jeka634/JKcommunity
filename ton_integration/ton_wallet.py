import requests
import json
import logging
from typing import Dict, Optional, List
from datetime import datetime
import hashlib
import base64

class TONWallet:
    def __init__(self, network: str = "mainnet"):
        self.network = network
        self.base_url = "https://toncenter.com/api/v2" if network == "mainnet" else "https://testnet.toncenter.com/api/v2"
        self.api_key = None
        
    def set_api_key(self, api_key: str):
        """Установка API ключа для TON Center"""
        self.api_key = api_key
    
    def get_wallet_info(self, wallet_address: str) -> Optional[Dict]:
        """Получение информации о кошельке"""
        try:
            url = f"{self.base_url}/getAddressInfo"
            params = {"address": wallet_address}
            if self.api_key:
                params["api_key"] = self.api_key
                
            response = requests.get(url, params=params)
            if response.status_code == 200:
                return response.json()
            else:
                logging.error(f"Error getting wallet info: {response.status_code}")
                return None
        except Exception as e:
            logging.error(f"Error getting wallet info: {e}")
            return None
    
    def get_balance(self, wallet_address: str) -> Optional[float]:
        """Получение баланса кошелька в TON"""
        try:
            wallet_info = self.get_wallet_info(wallet_address)
            if wallet_info and wallet_info.get("ok"):
                balance_nano = int(wallet_info["result"]["balance"])
                balance_ton = balance_nano / 1_000_000_000  # Конвертация из нанотонов в TON
                return balance_ton
            return None
        except Exception as e:
            logging.error(f"Error getting balance: {e}")
            return None
    
    def get_token_balance(self, wallet_address: str, token_address: str) -> Optional[float]:
        """Получение баланса токена (например, $gasJK)"""
        try:
            url = f"{self.base_url}/getTokenData"
            params = {
                "address": wallet_address,
                "token_address": token_address
            }
            if self.api_key:
                params["api_key"] = self.api_key
                
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    return float(data["result"]["balance"])
            return None
        except Exception as e:
            logging.error(f"Error getting token balance: {e}")
            return None
    
    def send_ton(self, from_wallet: str, to_wallet: str, amount: float, 
                 private_key: str, message: str = "") -> Optional[Dict]:
        """Отправка TON с одного кошелька на другой"""
        try:
            url = f"{self.base_url}/sendBoc"
            payload = {
                "boc": self._create_transaction_boc(from_wallet, to_wallet, amount, private_key, message)
            }
            if self.api_key:
                payload["api_key"] = self.api_key
                
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                return response.json()
            else:
                logging.error(f"Error sending TON: {response.status_code}")
                return None
        except Exception as e:
            logging.error(f"Error sending TON: {e}")
            return None
    
    def send_token(self, from_wallet: str, to_wallet: str, token_address: str, 
                   amount: float, private_key: str) -> Optional[Dict]:
        """Отправка токена (например, $gasJK)"""
        try:
            url = f"{self.base_url}/sendToken"
            payload = {
                "from": from_wallet,
                "to": to_wallet,
                "token_address": token_address,
                "amount": str(int(amount * 1_000_000_000)),  # Конвертация в нанотокены
                "private_key": private_key
            }
            if self.api_key:
                payload["api_key"] = self.api_key
                
            response = requests.post(url, json=payload)
            if response.status_code == 200:
                return response.json()
            else:
                logging.error(f"Error sending token: {response.status_code}")
                return None
        except Exception as e:
            logging.error(f"Error sending token: {e}")
            return None
    
    def get_nfts(self, wallet_address: str) -> List[Dict]:
        """Получение NFT кошелька"""
        try:
            url = f"{self.base_url}/getNFTs"
            params = {"address": wallet_address}
            if self.api_key:
                params["api_key"] = self.api_key
                
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    return data["result"]["nfts"]
            return []
        except Exception as e:
            logging.error(f"Error getting NFTs: {e}")
            return []
    
    def get_transactions(self, wallet_address: str, limit: int = 10) -> List[Dict]:
        """Получение истории транзакций кошелька"""
        try:
            url = f"{self.base_url}/getTransactions"
            params = {
                "address": wallet_address,
                "limit": limit
            }
            if self.api_key:
                params["api_key"] = self.api_key
                
            response = requests.get(url, params=params)
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    return data["result"]["transactions"]
            return []
        except Exception as e:
            logging.error(f"Error getting transactions: {e}")
            return []
    
    def validate_wallet_address(self, address: str) -> bool:
        """Валидация адреса TON кошелька"""
        try:
            # Базовая проверка формата TON адреса
            if not address.startswith(("EQ", "UQ", "0:")):
                return False
            
            # Проверка длины
            if len(address) < 48 or len(address) > 66:
                return False
            
            return True
        except Exception:
            return False
    
    def _create_transaction_boc(self, from_wallet: str, to_wallet: str, amount: float, 
                               private_key: str, message: str = "") -> str:
        """Создание BOC (Bag of Cells) для транзакции"""
        # Это упрощенная версия. В реальном проекте нужно использовать TON SDK
        try:
            # Конвертация в нанотоны
            amount_nano = int(amount * 1_000_000_000)
            
            # Создание простого BOC (в реальности это сложнее)
            transaction_data = {
                "from": from_wallet,
                "to": to_wallet,
                "amount": amount_nano,
                "message": message,
                "timestamp": int(datetime.now().timestamp())
            }
            
            # Создание хеша транзакции
            transaction_str = json.dumps(transaction_data, sort_keys=True)
            transaction_hash = hashlib.sha256(transaction_str.encode()).hexdigest()
            
            # В реальном проекте здесь была бы сложная логика создания BOC
            # Пока возвращаем заглушку
            return base64.b64encode(transaction_hash.encode()).decode()
            
        except Exception as e:
            logging.error(f"Error creating transaction BOC: {e}")
            return ""
    
    def get_gas_price(self) -> Optional[float]:
        """Получение текущей цены газа в TON"""
        try:
            url = f"{self.base_url}/getGasPrice"
            if self.api_key:
                url += f"?api_key={self.api_key}"
                
            response = requests.get(url)
            if response.status_code == 200:
                data = response.json()
                if data.get("ok"):
                    return float(data["result"]["gas_price"])
            return None
        except Exception as e:
            logging.error(f"Error getting gas price: {e}")
            return None
    
    def estimate_transaction_fee(self, from_wallet: str, to_wallet: str, 
                                amount: float, message: str = "") -> Optional[float]:
        """Оценка комиссии за транзакцию"""
        try:
            gas_price = self.get_gas_price()
            if gas_price is None:
                return None
            
            # Примерная оценка газа для простой транзакции
            estimated_gas = 10000  # базовый газ
            if message:
                estimated_gas += len(message) * 100  # дополнительный газ за сообщение
            
            fee = gas_price * estimated_gas / 1_000_000_000  # конвертация в TON
            return fee
        except Exception as e:
            logging.error(f"Error estimating transaction fee: {e}")
            return None 