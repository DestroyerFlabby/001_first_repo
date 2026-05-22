extends Node2D
class_name GameManager

const HEX_SIZE := 44.0
const PATH_COLOR := Color(0.1, 0.55, 1.0)
const TILE_COLOR := Color(0.16, 0.17, 0.2)
const TILE_BORDER := Color(0.42, 0.45, 0.52)
const NUMBER_COLOR := Color(0.12, 0.88, 0.48)
const NUMBER_REACHED_COLOR := Color(1.0, 0.28, 0.28)

@onready var grid_manager: GridManager = $GridManager
@onready var status_label: Label = $CanvasLayer/UI/StatusLabel
@onready var help_label: Label = $CanvasLayer/UI/HelpLabel
@onready var ui_root: Control = $CanvasLayer/UI

var level_data := LevelData.new()
var current_level_index: int = 0
var current_level: Dictionary = {}
var drawn_path: Array[Vector2i] = []
var active_drag := false
var next_number := 1
var game_started := false
var grid_origin := Vector2(360, 255)
var menu_panel: PanelContainer
var level_buttons: Array[Button] = []

func _ready() -> void:
	_build_menu()
	show_menu()
	queue_redraw()

func _build_menu() -> void:
	menu_panel = PanelContainer.new()
	menu_panel.name = "HomeMenu"
	menu_panel.set_anchors_preset(Control.PRESET_FULL_RECT)
	ui_root.add_child(menu_panel)

	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 44)
	margin.add_theme_constant_override("margin_top", 44)
	margin.add_theme_constant_override("margin_right", 44)
	margin.add_theme_constant_override("margin_bottom", 44)
	menu_panel.add_child(margin)

	var layout := VBoxContainer.new()
	layout.add_theme_constant_override("separation", 14)
	margin.add_child(layout)

	var title := Label.new()
	title.text = "Number Hex"
	title.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	title.add_theme_font_size_override("font_size", 34)
	layout.add_child(title)

	var subtitle := Label.new()
	subtitle.text = "Connect 1 to 10 in order. Never overlap your path."
	subtitle.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	layout.add_child(subtitle)

	var start_button := Button.new()
	start_button.text = "Start New Game"
	start_button.pressed.connect(func() -> void: start_level(0))
	layout.add_child(start_button)

	var level_label := Label.new()
	level_label.text = "Select Level"
	level_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	layout.add_child(level_label)

	var levels_grid := GridContainer.new()
	levels_grid.columns = 5
	layout.add_child(levels_grid)

	for i in range(level_data.get_level_count()):
		var button := Button.new()
		button.text = str(i + 1)
		button.custom_minimum_size = Vector2(72, 48)
		button.pressed.connect(func(level_index := i) -> void: start_level(level_index))
		levels_grid.add_child(button)
		level_buttons.append(button)

func show_menu() -> void:
	game_started = false
	active_drag = false
	menu_panel.visible = true
	status_label.text = ""
	help_label.text = ""
	queue_redraw()

func start_level(level_index: int) -> void:
	current_level_index = level_index
	current_level = level_data.get_level(current_level_index)
	drawn_path.clear()
	next_number = 1
	active_drag = false
	game_started = true
	menu_panel.visible = false
	grid_manager.setup(current_level["radius"], [])
	status_label.text = "%s: start at 1" % current_level["title"]
	help_label.text = "Drag from 1 to 10. Press R to reset or Esc for menu."
	queue_redraw()

func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventKey and event.pressed:
		if event.keycode == KEY_ESCAPE:
			show_menu()
			return
		if event.keycode == KEY_R and game_started:
			start_level(current_level_index)
			return

	if not game_started:
		return

	if event is InputEventMouseButton and event.button_index == MOUSE_BUTTON_LEFT:
		if event.pressed:
			start_drag(event.position)
		else:
			finish_drag()
	elif event is InputEventMouseMotion and active_drag:
		extend_drag(event.position)
	elif event is InputEventScreenTouch:
		if event.pressed:
			start_drag(event.position)
		else:
			finish_drag()
	elif event is InputEventScreenDrag and active_drag:
		extend_drag(event.position)

func start_drag(pointer_pos: Vector2) -> void:
	var coord := pointer_to_coord(pointer_pos)
	if not grid_manager.has_cell(coord):
		return
	if _number_at(coord) != 1:
		status_label.text = "Start on 1"
		return

	drawn_path = [coord]
	next_number = 2
	active_drag = true
	status_label.text = "Now connect 2"
	queue_redraw()

func extend_drag(pointer_pos: Vector2) -> void:
	var coord := pointer_to_coord(pointer_pos)
	if not grid_manager.has_cell(coord) or drawn_path.is_empty():
		return

	var last: Vector2i = drawn_path[drawn_path.size() - 1]
	if coord == last or not grid_manager.is_adjacent(last, coord):
		return

	if drawn_path.size() >= 2 and coord == drawn_path[drawn_path.size() - 2]:
		drawn_path.pop_back()
		_recalculate_next_number()
		_update_status()
		queue_redraw()
		return

	if drawn_path.has(coord):
		return

	var number := _number_at(coord)
	if number != -1 and number != next_number:
		status_label.text = "Connect %d next" % next_number
		return

	drawn_path.append(coord)
	if number == next_number:
		next_number += 1

	_update_status()
	queue_redraw()

func finish_drag() -> void:
	active_drag = false
	if next_number > 10:
		status_label.text = "Level Complete"

func _update_status() -> void:
	if next_number > 10:
		status_label.text = "Level Complete"
	elif drawn_path.size() > 0:
		status_label.text = "Now connect %d" % next_number

func _recalculate_next_number() -> void:
	next_number = 1
	for point: Dictionary in current_level["number_points"]:
		if drawn_path.has(point["coord"]) and point["number"] == next_number:
			next_number += 1

func _number_at(coord: Vector2i) -> int:
	if current_level.is_empty():
		return -1
	for point: Dictionary in current_level["number_points"]:
		if point["coord"] == coord:
			return point["number"]
	return -1

func pointer_to_coord(pointer_pos: Vector2) -> Vector2i:
	var nearest := Vector2i(999, 999)
	var nearest_distance := INF
	for coord: Vector2i in grid_manager.get_coords():
		var distance := pointer_pos.distance_to(coord_to_center(coord))
		if distance < nearest_distance:
			nearest = coord
			nearest_distance = distance
	if nearest_distance <= HEX_SIZE:
		return nearest
	return Vector2i(999, 999)

func coord_to_center(coord: Vector2i) -> Vector2:
	var x := HEX_SIZE * sqrt(3.0) * (coord.x + coord.y / 2.0)
	var y := HEX_SIZE * 1.5 * coord.y
	return grid_origin + Vector2(x, y)

func _draw() -> void:
	if not game_started:
		return
	draw_hex_grid()
	draw_path()
	draw_numbers()

func draw_hex_grid() -> void:
	for coord: Vector2i in grid_manager.get_coords():
		var points := _hex_points(coord_to_center(coord))
		draw_colored_polygon(points, TILE_COLOR)
		var outline := points
		outline.append(points[0])
		draw_polyline(outline, TILE_BORDER, 2.0, true)

func draw_path() -> void:
	if drawn_path.size() < 2:
		return
	for i in range(drawn_path.size() - 1):
		draw_line(coord_to_center(drawn_path[i]), coord_to_center(drawn_path[i + 1]), PATH_COLOR, 14.0, true)

func draw_numbers() -> void:
	for point: Dictionary in current_level["number_points"]:
		var coord: Vector2i = point["coord"]
		var number: int = point["number"]
		var center := coord_to_center(coord)
		var reached := drawn_path.has(coord)
		draw_circle(center, 20.0, NUMBER_REACHED_COLOR if reached else NUMBER_COLOR)
		draw_string(ThemeDB.fallback_font, center + Vector2(-7, 6), str(number), HORIZONTAL_ALIGNMENT_LEFT, -1, 18, Color.WHITE)

func _hex_points(center: Vector2) -> PackedVector2Array:
	var points := PackedVector2Array()
	for i in range(6):
		var angle := deg_to_rad(30.0 + 60.0 * i)
		points.append(center + Vector2(cos(angle), sin(angle)) * HEX_SIZE)
	return points
