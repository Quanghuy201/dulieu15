import threading
import time
import random
import string
from zlapi import ZaloAPI, ThreadType, Message, Mention
from config import API_KEY, SECRET_KEY, IMEI, SESSION_COOKIES
from collections import defaultdict

class Bot(ZaloAPI):
    def __init__(self, api_key, secret_key, imei=None, session_cookies=None):
        super().__init__(api_key, secret_key, imei, session_cookies)
        self.running = False

    def fetchGroupInfo(self):
        try:
            all_groups = self.fetchAllGroups()
            group_list = []
            for group_id, _ in all_groups.gridVerMap.items():
                group_info = super().fetchGroupInfo(group_id)
                group_name = group_info.gridInfoMap[group_id]["name"]
                group_list.append({'id': group_id, 'name': group_name})
            return group_list
        except Exception as e:
            print(f"Lỗi khi lấy danh sách nhóm: {e}")
            return []

    def display_group_menu(self):
        groups = self.fetchGroupInfo()
        if not groups:
            print("Không tìm thấy nhóm nào.")
            return None
        grouped = defaultdict(list)
        for group in groups:
            first_char = group['name'][0].upper()
            if first_char not in string.ascii_uppercase:
                first_char = '#'
            grouped[first_char].append(group)
        print("\nDanh sách các nhóm:")
        index_map = {}
        idx = 1
        for letter in sorted(grouped.keys()):
            print(f"\nNhóm {letter}:")
            for group in grouped[letter]:
                print(f"{idx}. {group['name']} (ID: {group['id']})")
                index_map[idx] = group['id']
                idx += 1
        return index_map

    def select_group(self):
        index_map = self.display_group_menu()
        if not index_map:
            return None
        while True:
            try:
                choice = int(input("Nhập số thứ tự của nhóm: ").strip())
                if choice in index_map:
                    return index_map[choice]
                print("Số không hợp lệ.")
            except ValueError:
                print("Vui lòng nhập số hợp lệ.")

    def list_group_members(self, thread_id):
        try:
            group = super().fetchGroupInfo(thread_id)["gridInfoMap"][thread_id]
            members = group["memVerList"]
            print("\n--- Danh sách thành viên ---")
            members_list = []
            for index, member in enumerate(members, start=1):
                uid = member.split('_')[0]
                user_info = super().fetchUserInfo(uid)
                author_info = user_info.get("changed_profiles", {}).get(uid, {})
                name = author_info.get('zaloName', 'Không xác định')
                members_list.append({"uid": uid, "name": name})
                print(f"{index}. {name} (UID: {uid})")
            raw_input = input("Nhập số để chọn thành viên (cách nhau bằng dấu phẩy nếu nhiều): ").strip()
            indices = [int(i) - 1 for i in raw_input.split(',') if i.strip().isdigit()]
            selected = [members_list[i] for i in indices if 0 <= i < len(members_list)]
            if selected:
                return selected
            print("❌ Không chọn được thành viên nào.")
            return None
        except Exception as e:
            print(f"Lỗi khi lấy danh sách thành viên: {e}")
            return None

    def send_reo_file(self, thread_id, users, filename, delay):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                base_lines = [line.strip() for line in f if line.strip()]
                if not base_lines:
                    print("❌ File rỗng hoặc không có dòng hợp lệ.")
                    return

            self.running = True
            remaining_lines = []
            user_index = 0

            def spam_loop():
                nonlocal remaining_lines, user_index
                while self.running:
                    if not remaining_lines:
                        remaining_lines = base_lines.copy()
                        random.shuffle(remaining_lines)
                    phrase = remaining_lines.pop()
                    current_user = users[user_index]
                    mentioned_name = current_user['name']
                    mentioned_user_id = current_user['uid']
                    mention_text = f"@{mentioned_name}"
                    message_text = f"{phrase} {mention_text}"
                    offset = message_text.index(mention_text)
                    mention = Mention(
                        uid=mentioned_user_id,
                        offset=offset,
                        length=len(mention_text)
                    )
                    full_message = Message(text=message_text, mention=mention)
                    self.send(full_message, thread_id=thread_id, thread_type=ThreadType.GROUP)
                    print(f"✅ Đã gửi: {mentioned_name}: {phrase}")
                    user_index = (user_index + 1) % len(users)
                    time.sleep(delay)

            thread = threading.Thread(target=spam_loop)
            thread.daemon = True
            thread.start()

            try:
                while self.running:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.stop_sending()

        except FileNotFoundError:
            print(f"❌ Không tìm thấy file: {filename}")
        except Exception as e:
            print(f"❌ Lỗi khi gửi nội dung: {e}")

    def stop_sending(self):
        self.running = False
        print("⛔ Đã dừng gửi tin nhắn.")

def run_tool():
    print("TOOL RÉO TAG TỪ FILE KHÔNG LẶP LẠI (NHIỀU NGƯỜI)")
    print("[1] Gửi nội dung từ file (có réo nhiều người)")
    print("[0] Thoát")
    choice = input("Nhập lựa chọn: ").strip()
    if choice != '1':
        print("Đã thoát tool.")
        return

    client = Bot(API_KEY, SECRET_KEY, IMEI, SESSION_COOKIES)
    thread_id = client.select_group()
    if not thread_id:
        return

    selected_users = client.list_group_members(thread_id)
    if not selected_users:
        return

    filename = input("Nhập tên file chứa nội dung: ").strip()
    try:
        delay = float(input("Nhập delay giữa các tin nhắn (giây): ").strip())
    except ValueError:
        print("⏱️ Dùng mặc định 10s.")
        delay = 10

    client.send_reo_file(
        thread_id=thread_id,
        users=selected_users,
        filename=filename,
        delay=delay
    )

if __name__ == "__main__":
    run_tool()
