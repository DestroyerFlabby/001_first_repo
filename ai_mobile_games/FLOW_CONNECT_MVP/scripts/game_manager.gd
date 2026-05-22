extends Node2D
class_name GameManager

@onready var grid_manager: GridManager = $GridManager
@onready var path_manager: PathManager = $PathManager
@onready var status_label: Label = $CanvasLayer/UI/StatusLabel

var level_data := LevelData.new()
var cell_size: int = 80
var grid_origin := Vector2(60, 60)

var active_path_id: int = -1

func _ready() -> void:
	# Build level and show initial state.
	load_level()
	status_label.text = "Draw paths to connect matching dots"
	queue_redraw()

func load_level() -> void:
	grid_manager.setup(level_data.grid_size, level_data.dot_pairs)
	path_manager.setup(level_data.dot_pairs.size())
	for path_id in range(level_data.dot_pairs.size()):
		var pair := level_data.dot_pairs[path_id]
		path_manager.add_coord(path_id, pair["start"])
		grid_manager.set_cell_path(pair["start"], path_id)
		path_manager.set_completed(path_id, false)

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed and event.keycode == KEY_R:
		reset_level()
	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		if event.pressed:
			start_drag(event.position)
		else:
			finish_drag()
	if event is InputEventMouseMotion and active_path_id != -1:
		extend_drag(event.position)

func reset_level() -> void:
	load_level()
	active_path_id = -1
	status_label.text = "Level reset"
	queue_redraw()

func start_drag(mouse_pos: Vector2) -> void:
	var coord := mouse_to_coord(mouse_pos)
	if not grid_manager.has_cell(coord):
		return
	var cell := grid_manager.get_cell(coord)
	if cell.is_dot:
		active_path_id = cell.dot_path_id
		grid_manager.clear_non_dot_cells(active_path_id)
		path_manager.clear_path(active_path_id)
		path_manager.add_coord(active_path_id, coord)

func extend_drag(mouse_pos: Vector2) -> void:
	var coord := mouse_to_coord(mouse_pos)
	if not grid_manager.has_cell(coord):
		return

	var path := path_manager.get_path(active_path_id)
	if path.is_empty():
		return
	var last: Vector2i = path[path.size() - 1]

	# Avoid diagonal movement.
	if coord == last or not grid_manager.is_adjacent(last, coord):
		return

	# Prevent path crossing/overlapping.
	if not grid_manager.is_cell_available_for_path(coord, active_path_id):
		return

	# Backtracking one step is allowed.
	if path.size() >= 2 and coord == path[path.size() - 2]:
		var removed: Vector2i = path.pop_back()
		if not grid_manager.get_cell(removed).is_dot:
			grid_manager.set_cell_path(removed, -1)
		path_manager.paths[active_path_id] = path
		queue_redraw()
		return

	path_manager.add_coord(active_path_id, coord)
	grid_manager.set_cell_path(coord, active_path_id)
	queue_redraw()

func finish_drag() -> void:
	if active_path_id == -1:
		return

	var path := path_manager.get_path(active_path_id)
	var pair := level_data.dot_pairs[active_path_id]
	var target: Vector2i = pair["end"]
	var completed := path.size() > 1 and path[path.size() - 1] == target
	path_manager.set_completed(active_path_id, completed)
	active_path_id = -1
	check_win()

func check_win() -> void:
	if path_manager.all_completed() and grid_manager.are_all_cells_filled():
		status_label.text = "Level Complete"
	else:
		status_label.text = "Keep going... (Press R to reset)"

func mouse_to_coord(mouse_pos: Vector2) -> Vector2i:
	var local := mouse_pos - grid_origin
	return Vector2i(floor(local.x / cell_size), floor(local.y / cell_size))

func coord_to_center(coord: Vector2i) -> Vector2:
	return grid_origin + Vector2(coord.x * cell_size + cell_size / 2, coord.y * cell_size + cell_size / 2)

func _draw() -> void:
	draw_grid()
	draw_paths()
	draw_dots()

func draw_grid() -> void:
	for y in range(level_data.grid_size):
		for x in range(level_data.grid_size):
			var pos := grid_origin + Vector2(x * cell_size, y * cell_size)
			draw_rect(Rect2(pos, Vector2(cell_size, cell_size)), Color(0.18, 0.18, 0.2), false, 2.0)

func draw_dots() -> void:
	for pair in level_data.dot_pairs:
		draw_circle(coord_to_center(pair["start"]), 16, pair["color"])
		draw_circle(coord_to_center(pair["end"]), 16, pair["color"])

func draw_paths() -> void:
	for path_id in path_manager.paths.keys():
		var path: Array = path_manager.paths[path_id]
		if path.size() < 2:
			continue
		var color: Color = level_data.dot_pairs[path_id]["color"]
		for i in range(path.size() - 1):
			draw_line(coord_to_center(path[i]), coord_to_center(path[i + 1]), color, 12.0)
