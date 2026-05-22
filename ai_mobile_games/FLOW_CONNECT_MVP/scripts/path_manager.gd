extends Node
class_name PathManager

var paths: Dictionary = {}
var completed_paths: Dictionary = {}

func setup(pair_count: int) -> void:
	paths.clear()
	completed_paths.clear()
	for i in range(pair_count):
		paths[i] = []
		completed_paths[i] = false

func clear_path(path_id: int) -> void:
	paths[path_id] = []
	completed_paths[path_id] = false

func add_coord(path_id: int, coord: Vector2i) -> void:
	var path: Array = paths[path_id]
	path.append(coord)
	paths[path_id] = path

func get_path(path_id: int) -> Array:
	return paths[path_id]

func set_completed(path_id: int, complete: bool) -> void:
	completed_paths[path_id] = complete

func all_completed() -> bool:
	for complete in completed_paths.values():
		if not complete:
			return false
	return true
