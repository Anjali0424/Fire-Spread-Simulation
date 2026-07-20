from flask import Flask, render_template, jsonify
from fire_simulation import SimulationEngine

app = Flask(__name__)

engine = SimulationEngine()  # creates nothing heavy until requested

@app.route('/')
def index():
    return render_template('index.html')

# Initialize / get a fresh random scenario (grid, walls, exits, humans)
@app.route('/init')
def init_map():
    engine.create_random_scenario()
    payload = engine.get_initial_state()
    return jsonify(payload)

# Prepare full simulation frames (Python DSA does all BFS/updates)
# returns frames list + tickMs
@app.route('/simulate')
def simulate():
    frames, tick_ms = engine.simulate_full()  # runs core DSA simulation and returns frames
    return jsonify({"frames": frames, "tick_ms": tick_ms})

if __name__ == "__main__":
    app.run(debug=True)
