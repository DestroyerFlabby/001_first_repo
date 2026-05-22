extends Node
class_name GridManager

const CellData = preload("res://scripts/cell.gd")
const HEX_DIRECTIONS: Array[Vector2i] = [
	Vector2i(1, 0),
	Vector2i(-1, 0),
	Vector2i(0, 1),
	Vector2i(0, -1),
	Vector2i(1, -1),
	Vector2i(-1, 1)
]

var radius: int = 2
var cells: Dictionary = {}

func setup(hex_radius: int, dot_pairs: Array[Dictionary]) -> void:
	radius = hex_radius
	cells.clear()

	for q in range(-radius, radius + 1):
		for r in range(-radius, radius + 1):
			var coord := Vector2i(q, r)
			if _is_inside_hex(coord):
				cells[coord] = CellData.new(coord)

	for path_id in range(dot_pairs.size()):
		var pair := dot_pairs[path_id]
		mark_dot(pair["start"], path_id)
		mark_dot(pair["end"], path_id)

func mark_dot(coord: Vector2i, path_id: int) -> void:
	var cell: Cell = cells.get(coord)
	if cell == null:
		return
	cell.is_dot = true
	cell.dot_path_id = path_id

func has_cell(coord: Vector2i) -> bool:
	return cells.has(coord)

func get_cell(coord: Vector2i) -> Cell:
	return cells.get(coord)

func get_coords() -> Array:
	return cells.keys()

func is_adjacent(a: Vector2i, b: Vector2i) -> bool:
	return HEX_DIRECTIONS.has(b - a)

func is_cell_available_for_path(coord: Vector2i, path_id: int) -> bool:
	var cell := get_cell(coord)
	if cell == null:
		return false
	if cell.occupying_path_id != -1 and cell.occupying_path_id != path_id:
		return false
	if cell.is_dot and cell.dot_path_id != path_id:
		return false
	return true

func set_cell_path(coord: Vector2i, path_id: int) -> void:
	var cell := get_cell(coord)
	if cell != null:
		cell.occupying_path_id = path_id

func clear_non_dot_cells(path_id: int) -> void:
	for cell: Cell in cells.values():
		if cell.occupying_path_id == path_id and not cell.is_dot:
			cell.occupying_path_id = -1

func are_all_cells_filled() -> bool:
	for cell: Cell in cells.values():
		if cell.occupying_path_id == -1:
			return false
	return true

func _is_inside_hex(coord: Vector2i) -> bool:
	return max(abs(coord.x), abs(coord.y), abs(-coord.x - coord.y)) <= radius
