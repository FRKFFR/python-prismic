import tkinter as tk
from tkinter import ttk, messagebox
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests
from PIL import Image, ImageTk, ImageDraw, ImageFont, UnidentifiedImageError
import io
import json
import threading
import webbrowser
import logging

# Setup logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Config
auth_cookie = "authcookie_XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX" # Replace with your authcookie, how to find your authcookie install https://chromewebstore.google.com/detail/editthiscookie-v3/ojfebgpkimhlhcblbalbfjblapadhbol/reviews
user_id = "usr_XXXXXXXX-XXXX-XXXX-XXXX-XXXXXXXXXXXX"  # Replace with your user ID how to find you user id, in README

# Columns and row
COLUMNS = 10
ROWS = 10

# Multilpication for the number of avartar to load 
AVATARS_PER_PAGE = COLUMNS * ROWS

# Load avatars
with open('all_decoded_avatars_full.json', 'r', encoding='utf-8') as f:
    avatars_data = json.load(f)
    logging.info(f"Loaded {len(avatars_data)} avatars.")

# Globals
filtered_avatars = avatars_data
current_page = 0
avatar_widgets = []
banned_avatars_count = 0  # Counter for banned/deleted avatars

# Tkinter setup
root = tk.Tk()
root.title("VRChat Avatar Browser Prismic database By FR_KF_FR")
root.geometry("1800x1000")

# Frame for loading at the bottom left
loading_frame = tk.Frame(root, width=200, height=50)
loading_frame.pack(side="bottom", anchor="w", padx=10, pady=10)

# Loading
loading_label = tk.Label(loading_frame, text="Loading Avatars...", font=("Arial", 12))
progress_var_avatars = tk.DoubleVar()  # Progress for avatar data
progress_bar_avatars = ttk.Progressbar(loading_frame, variable=progress_var_avatars, maximum=100, length=180)

progress_var_images = tk.DoubleVar()  # Progress for image fetching
progress_bar_images = ttk.Progressbar(loading_frame, variable=progress_var_images, maximum=100, length=180)

# Banned avatars counter
banned_count_label = tk.Label(loading_frame, text=f"Banned Avatars: {banned_avatars_count}", font=("Arial", 12))
banned_count_label.pack(side="left", padx=10)

# Frame for search and filters
filter_frame = tk.Frame(root)
filter_frame.pack(pady=10)

# --- [ADDED] ---
# Frame for Current Avatar Info (inside filter frame)
current_avatar_frame = tk.Frame(filter_frame)
current_avatar_frame.grid(row=0, column=0, rowspan=2, padx=10, pady=5, sticky="w")

current_avatar_img_label = tk.Label(current_avatar_frame)
current_avatar_img_label.pack(side="top", pady=5)

current_avatar_name_label = tk.Label(current_avatar_frame, text="Current Avatar", font=("Arial", 12, "bold"), wraplength=100)
current_avatar_name_label.pack(side="top")
# --- [END ADD] ---

# Name/Description Search
search_var = tk.StringVar()
search_entry = tk.Entry(filter_frame, textvariable=search_var, font=("Arial", 14), width=50)
search_label = tk.Label(filter_frame, text="Search Name/Description:", font=("Arial", 12))

# Author Search
author_var = tk.StringVar()
author_entry = tk.Entry(filter_frame, textvariable=author_var, font=("Arial", 14), width=50)
author_label = tk.Label(filter_frame, text="Search Author:", font=("Arial", 12))

# Platform filter checkboxes
platforms_var = {"PC": tk.BooleanVar(), "Quest": tk.BooleanVar(), "iOS": tk.BooleanVar()}
platforms_frame = tk.LabelFrame(filter_frame, text="Filter by Platforms", font=("Arial", 12), padx=10, pady=10)

pc_checkbox = tk.Checkbutton(platforms_frame, text="PC", variable=platforms_var["PC"])
quest_checkbox = tk.Checkbutton(platforms_frame, text="Quest", variable=platforms_var["Quest"])
ios_checkbox = tk.Checkbutton(platforms_frame, text="iOS", variable=platforms_var["iOS"])

# Page navigation buttons
page_nav_frame = tk.Frame(filter_frame)
prev_button = tk.Button(page_nav_frame, text="Previous", command=lambda: change_page(-1))
prev_button.grid(row=0, column=0, padx=5)

page_label = tk.Label(page_nav_frame, text="Page 1")
page_label.grid(row=0, column=1, padx=5)

next_button = tk.Button(page_nav_frame, text="Next", command=lambda: change_page(1))
next_button.grid(row=0, column=2, padx=5)

# --- [SHIFT EVERYTHING RIGHT BY 1 COLUMN] ---
search_label.grid(row=0, column=1, padx=5, pady=5)
search_entry.grid(row=1, column=1, padx=5, pady=5)
author_label.grid(row=0, column=2, padx=5, pady=5)
author_entry.grid(row=1, column=2, padx=5, pady=5)
platforms_frame.grid(row=0, column=3, rowspan=2, padx=5, pady=5)
pc_checkbox.grid(row=0, column=0, padx=10, pady=5)
quest_checkbox.grid(row=0, column=1, padx=10, pady=5)
ios_checkbox.grid(row=0, column=2, padx=10, pady=5)
page_nav_frame.grid(row=0, column=4, rowspan=2, padx=5, pady=5)

# Search Button
search_button = tk.Button(filter_frame, text="Search", command=lambda: filter_avatars(0))
search_button.grid(row=2, column=0, columnspan=5, pady=10)

# Scrollable frame
canvas = tk.Canvas(root)
scrollbar = ttk.Scrollbar(root, orient="vertical", command=canvas.yview)
scrollable_frame = ttk.Frame(canvas)

scrollable_frame.bind(
    "<Configure>",
    lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
)

canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
canvas.configure(yscrollcommand=scrollbar.set)
canvas.pack(side="left", fill="both", expand=True)
scrollbar.pack(side="right", fill="y")

# Enable mouse scrolling
def on_mouse_wheel(event):
    canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    canvas.update_idletasks()

canvas.bind_all("<MouseWheel>", on_mouse_wheel)

# Clear widgets
def clear_frame():
    global avatar_widgets
    for widget in avatar_widgets:
        widget.destroy()
    avatar_widgets = []

def fetch_current_avatar(auth_cookie):
    try:
        logging.debug(f"Fetching currently equipped avatar for user {user_id}")
        r = requests.get(
            f"https://api.vrchat.cloud/api/1/users/{user_id}/avatar",
            headers={"Cookie": f"auth={auth_cookie}", "User-Agent": "VRChatAPI/1.0"}
        )
        if r.status_code == 200:
            return r.json()
        else:
            logging.error(f"Failed to fetch current avatar: Status {r.status_code}")
            return None
    except Exception as e:
        logging.error(f"Error fetching current avatar: {e}")
        return None

def load_current_avatar():
    try:
        headers = {
            "Cookie": f"auth={auth_cookie}",
            "User-Agent": "VRChat/2024.1.2"  # Fake being VRChat client
        }
        # Get the current user data
        user_response = requests.get("https://api.vrchat.cloud/api/1/auth/user", headers=headers)
        user_response.raise_for_status()
        user_data = user_response.json()
        
        current_avatar_id = user_data.get('currentAvatar')
        if not current_avatar_id:
            logging.warning("No current avatar found in user data.")
            return

        # Get the avatar details
        avatar_response = requests.get(f"https://api.vrchat.cloud/api/1/avatars/{current_avatar_id}", headers=headers)
        avatar_response.raise_for_status()
        avatar_data = avatar_response.json()

        # Load the avatar image
        image_url = avatar_data.get('imageUrl') or avatar_data.get('thumbnailImageUrl')
        if not image_url:
            logging.warning("No image URL for current avatar.")
            return

        img_response = requests.get(image_url, headers=headers)
        img_data = img_response.content
        img = Image.open(io.BytesIO(img_data)).convert("RGBA")
        img = img.resize((100, 100), Image.LANCZOS)
        img = ImageTk.PhotoImage(img)

        # Update the UI
        current_avatar_img_label.config(image=img)
        current_avatar_img_label.image = img
        current_avatar_name_label.config(text=avatar_data['name'])

    except Exception as e:
        logging.error(f"Failed to load current avatar: {e}")

def fetch_avatar_details(avatar_id):
    global banned_avatars_count
    try:
        logging.debug(f"Fetching details for avatar {avatar_id}")
        r = requests.get(f"https://api.vrchat.cloud/api/1/avatars/{avatar_id}",
                         headers={"Cookie": f"auth={auth_cookie}", "User-Agent": "VRChatAPI/1.0"})
        if r.status_code == 200:
            return r.json()
        elif r.status_code == 404:  # Banned or deleted avatar
            banned_avatars_count += 1
            banned_count_label.config(text=f"Banned Avatars: {banned_avatars_count}")
            return None
        else:
            logging.error(f"Failed to fetch avatar {avatar_id}: Status {r.status_code}")
    except Exception as e:
        logging.error(f"Error fetching {avatar_id}: {e}")
    return None

def fetch_avatar_image(image_url, platforms):
    try:
        logging.debug(f"Fetching image {image_url}")
        img_response = requests.get(image_url, headers={"Cookie": f"auth={auth_cookie}", "User-Agent": "VRChatAPI/1.0"})
        img_data = img_response.content
        img = Image.open(io.BytesIO(img_data)).convert("RGBA")
        img = img.resize((120, 120))

        # Draw platform text
        draw = ImageDraw.Draw(img)
        font = ImageFont.load_default()
        platform_colors = {
            "PC": "blue",
            "Quest": "green",
            "iOS": "purple"
        }
        y = 2
        for platform in platforms:
            text = platform
            color = platform_colors.get(platform, "white")
            bbox = draw.textbbox((0, 0), text, font=font)
            w, h = bbox[2] - bbox[0], bbox[3] - bbox[1]
            draw.rectangle([120-w-8, y, 120-2, y+h+2], fill="black")
            draw.text((120-w-5, y), text, font=font, fill=color)
            y += h + 4

        return ImageTk.PhotoImage(img)
    except (UnidentifiedImageError, Exception) as e:
        logging.error(f"Error loading image: {e}")
        img = Image.new('RGBA', (120, 120), color='gray')
        return ImageTk.PhotoImage(img)

def show_info(avatar):
    info = f"Name: {avatar['name']}\nAuthor: {avatar['author']}\nDescription: {avatar['description']}"
    messagebox.showinfo("Avatar Info", info)

def open_avatar_page(avatar_id):
    url = f"https://vrchat.com/home/avatar/{avatar_id}"
    webbrowser.open(url)

def filter_avatars(page):
    global filtered_avatars, current_page
    name_desc_query = search_var.get().lower()
    author_query = author_var.get().lower()

    logging.debug(f"Filtering avatars with Name/Description '{name_desc_query}' and Author '{author_query}'")

    filtered_avatars = [
        avatar for avatar in avatars_data
        if (name_desc_query in avatar['name'].lower() or name_desc_query in avatar['description'].lower())
        and (author_query in avatar['author'].lower())
    ]

    selected_platforms = [platform for platform, var in platforms_var.items() if var.get()]
    if selected_platforms:
        filtered_avatars = [
            avatar for avatar in filtered_avatars
            if any(platform in selected_platforms for platform in avatar['platforms'])
        ]

    logging.debug(f"{len(filtered_avatars)} avatars matched the filters.")

    current_page = page
    threaded_display_avatars(current_page)

# Define the function to handle selecting the avatar
def select_avatar(avatar_id):
    url = f"https://api.vrchat.cloud/api/1/avatars/{avatar_id}/select"
    headers = {
        "Cookie": f"auth={auth_cookie}",
        "User-Agent": "VRChatAPI/1.0"
    }
    try:
        # Send the PUT request to select the avatar
        response = requests.put(url, headers=headers)
        
        if response.status_code == 200:
            logging.info(f"Avatar {avatar_id} selected successfully.")
            messagebox.showinfo("Success", f"Avatar {avatar_id} selected successfully!")
            
            # 🟰 Refresh the current avatar display
            load_current_avatar()

        else:
            logging.error(f"Failed to select avatar {avatar_id}: {response.status_code}")
            messagebox.showerror("Error", f"Failed to select avatar {avatar_id}. Status: {response.status_code}")

    except Exception as e:
        logging.error(f"Error selecting avatar {avatar_id}: {e}")
        messagebox.showerror("Error", f"Error selecting avatar {avatar_id}: {str(e)}")

# Update the "display_avatars" function to include the Select button
def display_avatars(page):
    logging.debug(f"Displaying avatars for page {page + 1}")
    clear_frame()

    start = page * AVATARS_PER_PAGE
    end = start + AVATARS_PER_PAGE
    avatars_to_display = filtered_avatars[start:end]

    row = 0
    col = 0

    futures = []
    total_avatars = len(avatars_to_display)

    with ThreadPoolExecutor(max_workers=10) as executor:
        details_futures = {executor.submit(fetch_avatar_details, avatar['avatar_id']): avatar for avatar in avatars_to_display}
        
        for future in as_completed(details_futures):
            avatar = details_futures[future]
            details = future.result()

            if details:
                # Get the avatar image URL
                image_url = details.get('imageUrl') or details.get('thumbnailImageUrl')
                if not image_url:
                    continue

                # Fetch the image in parallel
                img_future = executor.submit(fetch_avatar_image, image_url, avatar['platforms'])
                img = img_future.result()  # Get the image when ready

                # Create a new avatar container widget and show image immediately
                container = tk.Frame(scrollable_frame, bd=2, relief=tk.RIDGE, width=180, height=270)
                container.grid(row=row, column=col, padx=5, pady=5)
                container.grid_propagate(False)

                avatar_label = tk.Label(container, image=img)
                avatar_label.image = img
                avatar_label.pack(pady=5)

                name_label = tk.Label(container, text=avatar['name'], font=("Arial", 10, "bold"), wraplength=160)
                name_label.pack()

                description_label = tk.Label(container, text=avatar['description'], font=("Arial", 8),
                                             wraplength=160, justify="left")
                description_label.pack(pady=3)

                buttons_frame = tk.Frame(container)
                buttons_frame.pack()

                info_button = tk.Button(buttons_frame, text="?", width=2, command=lambda a=avatar: show_info(a))
                info_button.pack(side="left", padx=5)

                select_button = tk.Button(buttons_frame, text="Open Web", command=lambda id=avatar['avatar_id']: open_avatar_page(id))
                select_button.pack(side="right", padx=5)

                # Add the Select button
                select_button = tk.Button(buttons_frame, text="Select", command=lambda id=avatar['avatar_id']: select_avatar(id))
                select_button.pack(side="right", padx=5)

                avatar_widgets.append(container)

                col += 1
                if col >= COLUMNS:
                    col = 0
                    row += 1

                # Update progress bars
                progress_var_avatars.set(((len(futures) + 1) / total_avatars) * 100)
                progress_bar_avatars.update()

                progress_var_images.set(((len(futures) + 1) / total_avatars) * 100)
                progress_bar_images.update()

                # Force Tkinter to refresh the UI
                root.after(10)

    # Hide loading bars when done
    loading_label.place_forget()
    progress_bar_avatars.place_forget()
    progress_bar_images.place_forget()

    page_label.config(text=f"Page {current_page + 1} / {max(1, (len(filtered_avatars) + AVATARS_PER_PAGE - 1) // AVATARS_PER_PAGE)}")

def threaded_display_avatars(page):
    loading_label.pack(side="left", padx=10, pady=5)
    progress_bar_avatars.pack(side="left", padx=10, pady=5)
    progress_bar_images.pack(side="left", padx=10, pady=5)

    # Start thread for displaying avatars
    threading.Thread(target=lambda: display_avatars(page), daemon=True).start()

def change_page(direction):
    global current_page
    new_page = current_page + direction
    if 0 <= new_page < len(filtered_avatars) // AVATARS_PER_PAGE + 1:
        current_page = new_page
        threaded_display_avatars(current_page)

load_current_avatar()
root.mainloop()