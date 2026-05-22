extends RefCounted
class_name Cell

var coord: Vector2i
var occupying_path_id: int = -1
var is_dot: bool = false
var dot_path_id: int = -1

func _init(cell_coord: Vector2i) -> void:
	coord = cell_coord
