import os
import shutil
from tkinter import Tk, Label, Entry, Button, filedialog, StringVar, OptionMenu, messagebox
import pandas as pd

# Function to save player details
def save_player():
    player_name = name_var.get().strip()
    if len(player_name) == 0:
        messagebox.showerror("Error", "Player name cannot be empty.")
        return
    if len(player_name) > 15:
        messagebox.showerror("Error", "Player name must be 15 characters or less.")
        return

    age = age_var.get().strip()
    tshirt_size = tshirt_var.get()
    jersey_number = jersey_var.get().strip()
    role = role_var.get()
    photo_path = photo_var.get()

    if not photo_path:
        messagebox.showerror("Error", "Please select a photo.")
        return

    # Create folder for player
    folder_name = player_name.replace(" ", "_")  # Avoid spaces in folder names
    if not os.path.exists(folder_name):
        os.makedirs(folder_name)

    # Copy photo to folder
    photo_filename = os.path.basename(photo_path)
    dest_photo_path = os.path.join(folder_name, photo_filename)
    shutil.copy(photo_path, dest_photo_path)

    # Create Excel file with details
    data = {
        "Name": [player_name],
        "Age": [age],
        "Tshirt Size": [tshirt_size],
        "Jersey Number": [jersey_number],
        "Role": [role],
        "Photo": [photo_filename]
    }
    df = pd.DataFrame(data)
    excel_path = os.path.join(folder_name, f"{player_name}.xlsx")
    df.to_excel(excel_path, index=False)

    messagebox.showinfo("Success", f"Player {player_name} saved successfully!")

# Function to select photo
def select_photo():
    file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.png;*.jpg;*.jpeg")])
    if file_path:
        photo_var.set(file_path)

# GUI setup
root = Tk()
root.title("Player Details Form")
root.geometry("400x400")

name_var = StringVar()
age_var = StringVar()
tshirt_var = StringVar(value="M")
jersey_var = StringVar()
role_var = StringVar(value="Batsman")
photo_var = StringVar()

Label(root, text="Player Name (≤15 chars):").pack()
Entry(root, textvariable=name_var).pack()

Label(root, text="Age:").pack()
Entry(root, textvariable=age_var).pack()

Label(root, text="Tshirt Size:").pack()
OptionMenu(root, tshirt_var, "S", "M", "L", "XL", "XXL", "XXXL").pack()

Label(root, text="Jersey Number:").pack()
Entry(root, textvariable=jersey_var).pack()

Label(root, text="Role:").pack()
OptionMenu(root, role_var, "Batsman", "Bowler", "Allrounder").pack()

Label(root, text="Photo:").pack()
Button(root, text="Select Photo", command=select_photo).pack()

Button(root, text="Save Player", command=save_player, bg="green", fg="white").pack(pady=20)

root.mainloop()
