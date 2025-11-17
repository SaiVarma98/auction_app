from flask import Flask, render_template, request, redirect, url_for, session, jsonify
import json
import os

app = Flask(__name__)
app.secret_key = "supersecretkey"

# JSON paths
USERS_FILE = "data/users.json"
TEAMS_FILE = "data/teams.json"
PLAYERS_FILE = "data/players.json"
AUCTION_STATE_FILE = "data/auction_state.json"

# ---------------- JSON Helpers ----------------
def safe_read(file, default=None):
    if not os.path.exists(file):
        return default if default is not None else []
    try:
        with open(file, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return default if default is not None else []
            return json.loads(content)
    except Exception as e:
        print(f"Error reading {file}: {e}")
        return default if default is not None else []

def safe_write(file, data):
    try:
        with open(file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
    except Exception as e:
        print(f"Error writing {file}: {e}")

def get_auction_state():
    state = safe_read(AUCTION_STATE_FILE, {"current_player_id": None, "highest_bid": 0, "highest_bidder": None, "status": "not_started"})
    return state

def set_auction_state(state):
    safe_write(AUCTION_STATE_FILE, state)

def get_current_player():
    state = get_auction_state()
    players = safe_read(PLAYERS_FILE, [])
    if state.get("current_player_id") is None:
        return None
    return next((p for p in players if p["id"] == state["current_player_id"]), None)

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET","POST"])
def login():
    if request.method=="POST":
        username = request.form.get("username")
        password = request.form.get("password")
        users = safe_read(USERS_FILE)
        user = next((u for u in users if u["username"]==username and u["password"]==password), None)
        if user:
            session["username"] = username
            session["role"] = user["role"]
            if user["role"]=="bidder":
                session["team_name"] = user.get("team_name")
                return redirect(url_for("bidder_dashboard"))
            elif user["role"]=="auctioneer":
                return redirect(url_for("auctioneer_dashboard"))
            elif user["role"]=="admin":
                return redirect(url_for("admin_dashboard"))
        else:
            return render_template("login.html", error="Invalid credentials")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ---------------- DASHBOARDS ----------------
@app.route("/auctioneer")
def auctioneer_dashboard():
    if session.get("role") != "auctioneer":
        return redirect(url_for("login"))
    return render_template("auctioneer.html")

@app.route("/bidder")
def bidder_dashboard():
    if session.get("role") != "bidder":
        return redirect(url_for("login"))
    return render_template("bidder.html", team_name=session.get("team_name",""))

@app.route("/admin")
def admin_dashboard():
    if session.get("role") != "admin":
        return redirect(url_for("login"))
    return render_template("admin.html")

@app.route("/view")
def public_viewer():
    return render_template("viewer.html")

# ---------------- AUCTION ACTIONS ----------------
@app.route("/start_auction")
def start_auction():
    state = get_auction_state()
    if state["status"] == "not_started":
        players = safe_read(PLAYERS_FILE, [])
        first = next((p for p in players if not p.get("sold", False)), None)
        if first:
            state["current_player_id"] = first["id"]
            state["highest_bid"] = first["base_price"]
            state["highest_bidder"] = None
            state["status"] = "in_progress"
            set_auction_state(state)
    return redirect(url_for("auctioneer_dashboard"))

@app.route("/next_player")
def next_player():
    state = get_auction_state()
    players = safe_read(PLAYERS_FILE, [])
    unsold = [p for p in players if not p.get("sold", False) and p["id"] != state.get("current_player_id")]
    if unsold:
        next_p = unsold[0]
        state["current_player_id"] = next_p["id"]
        state["highest_bid"] = next_p["base_price"]
        state["highest_bidder"] = None
        state["status"] = "in_progress" if next_p["round"]==1 else "round2"
    else:
        state["current_player_id"] = None
        state["highest_bid"] = 0
        state["highest_bidder"] = None
        state["status"] = "finished"
    set_auction_state(state)
    return redirect(url_for("auctioneer_dashboard"))

@app.route("/pass_player")
def pass_player():
    player = get_current_player()
    if player:
        if player.get("round",1) == 1:
            player["round"] = 2
        players = safe_read(PLAYERS_FILE, [])
        safe_write(PLAYERS_FILE, players)
    return next_player()

@app.route("/finalize_sale")
def finalize_sale():
    state = get_auction_state()
    player = get_current_player()
    if player and state.get("highest_bidder"):
        player["sold"] = True
        player["sold_to"] = state["highest_bidder"]
        player["final_price"] = state["highest_bid"]
        teams = safe_read(TEAMS_FILE, [])
        team = next((t for t in teams if t["team_name"]==state["highest_bidder"]), None)
        if team:
            team["purse"] -= state["highest_bid"]
        players = safe_read(PLAYERS_FILE, [])
        safe_write(PLAYERS_FILE, players)
        safe_write(TEAMS_FILE, teams)
        state["highest_bid"] = 0
        state["highest_bidder"] = None
        set_auction_state(state)
    return redirect(url_for("auctioneer_dashboard"))

@app.route("/start_round2")
def start_round2():
    players = safe_read(PLAYERS_FILE, [])
    round2 = [p for p in players if not p.get("sold", False) and p.get("round",1)==2]
    if round2:
        state = get_auction_state()
        state["current_player_id"] = round2[0]["id"]
        state["highest_bid"] = round2[0]["base_price"]
        state["highest_bidder"] = None
        state["status"] = "round2"
        set_auction_state(state)
    return redirect(url_for("auctioneer_dashboard"))

@app.route("/reset_auction")
def reset_auction():
    players = safe_read(PLAYERS_FILE, [])
    for p in players:
        p["sold"] = False
        p["sold_to"] = None
        p["round"] = 1
        p["final_price"] = 0
    safe_write(PLAYERS_FILE, players)

    teams = safe_read(TEAMS_FILE, [])
    for t in teams:
        t["purse"] = 10000
    safe_write(TEAMS_FILE, teams)

    state = {"current_player_id": None, "highest_bid": 0, "highest_bidder": None, "status": "not_started"}
    set_auction_state(state)
    return redirect(url_for("auctioneer_dashboard"))

# ---------------- BID ACTION ----------------
@app.route("/place_bid", methods=["POST"])
def place_bid():
    data = request.json
    team_name = data.get("team")
    try:
        amount = int(data.get("amount"))
    except:
        return jsonify({"status":"error","message":"Invalid bid"})
    state = get_auction_state()
    player = get_current_player()
    if not player or state.get("status") not in ["in_progress","round2"]:
        return jsonify({"status":"error","message":"No active player"})
    teams = safe_read(TEAMS_FILE, [])
    team = next((t for t in teams if t["team_name"]==team_name), None)
    if not team or team["purse"] < amount or amount <= state.get("highest_bid",0):
        return jsonify({"status":"error","message":"Invalid bid"})
    state["highest_bid"] = amount
    state["highest_bidder"] = team_name
    set_auction_state(state)
    return jsonify({"status":"success"})

# ---------------- LIVE STATE ----------------
@app.route("/live_state")
def live_state():
    players = safe_read(PLAYERS_FILE, [])
    teams = safe_read(TEAMS_FILE, [])
    state = get_auction_state()
    current_player = None
    if state.get("current_player_id") is not None:
        current_player = next((p for p in players if p["id"]==state["current_player_id"]), None)
    return jsonify({
        "current_player": current_player,
        "state": state,
        "players": players,
        "teams": teams
    })

# ---------------- ADMIN ----------------
@app.route("/add_user", methods=["POST"])
def add_user():
    if session.get("role")!="admin":
        return redirect(url_for("login"))
    username = request.form.get("username")
    password = request.form.get("password")
    role = request.form.get("role")
    users = safe_read(USERS_FILE, [])
    if username and password and role:
        users.append({"username":username, "password":password, "role":role})
        safe_write(USERS_FILE, users)
    return redirect(url_for("admin_dashboard"))

@app.route("/add_team", methods=["POST"])
def add_team():
    if session.get("role")!="admin":
        return redirect(url_for("login"))
    team_name = request.form.get("team_name")
    purse = int(request.form.get("purse",10000))
    teams = safe_read(TEAMS_FILE, [])
    if team_name:
        teams.append({"team_name":team_name,"purse":purse})
        safe_write(TEAMS_FILE, teams)
    return redirect(url_for("admin_dashboard"))

@app.route("/add_player", methods=["POST"])
def add_player():
    if session.get("role")!="admin":
        return redirect(url_for("login"))
    name = request.form.get("name")
    role = request.form.get("role")
    base_price = int(request.form.get("base_price",100))
    image_file = request.files.get("image")
    players = safe_read(PLAYERS_FILE, [])
    if image_file:
        filename = f"{name.replace(' ','_')}.png"
        os.makedirs("static/images", exist_ok=True)
        image_file.save(os.path.join("static/images", filename))
    else:
        filename = "default.png"
    if name and role:
        new_id = max([p.get("id",0) for p in players], default=0)+1
        players.append({"id":new_id,"name":name,"role":role,"base_price":base_price,"image":filename,
                        "sold":False,"sold_to":None,"round":1,"final_price":0})
        safe_write(PLAYERS_FILE, players)
    return redirect(url_for("admin_dashboard"))

# ---------------- RUN APP ----------------
if __name__=="__main__":
    os.makedirs("data", exist_ok=True)
    os.makedirs("static/images", exist_ok=True)
    app.run(host="0.0.0.0", port=5000, debug=True)
