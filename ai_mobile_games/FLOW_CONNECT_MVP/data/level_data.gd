extends Resource
class_name LevelData

const CHECKPOINT_INDICES: Array[int] = [0, 2, 4, 6, 8, 10, 12, 14, 16, 18]

var base_solution_path: Array[Vector2i] = [
	Vector2i(0, -2),
	Vector2i(1, -2),
	Vector2i(2, -2),
	Vector2i(2, -1),
	Vector2i(1, -1),
	Vector2i(0, -1),
	Vector2i(-1, -1),
	Vector2i(-2, 0),
	Vector2i(-1, 0),
	Vector2i(0, 0),
	Vector2i(1, 0),
	Vector2i(2, 0),
	Vector2i(1, 1),
	Vector2i(0, 1),
	Vector2i(-1, 1),
	Vector2i(-2, 1),
	Vector2i(-2, 2),
	Vector2i(-1, 2),
	Vector2i(0, 2)
]

var level_specs: Array[Dictionary] = [
	{"title": "Level 1", "rotation": 0, "mirror": false, "reverse": false},
	{"title": "Level 2", "rotation": 1, "mirror": false, "reverse": false},
	{"title": "Level 3", "rotation": 2, "mirror": false, "reverse": false},
	{"title": "Level 4", "rotation": 3, "mirror": false, "reverse": false},
	{"title": "Level 5", "rotation": 4, "mirror": false, "reverse": false},
	{"title": "Level 6", "rotation": 5, "mirror": false, "reverse": false},
	{"title": "Level 7", "rotation": 0, "mirror": true, "reverse": false},
	{"title": "Level 8", "rotation": 2, "mirror": true, "reverse": false},
	{"title": "Level 9", "rotation": 4, "mirror": true, "reverse": false},
	{
		"title": "Level 10",
		"rotation": 3,
		"mirror": true,
		"reverse": true,
		"checkpoints": [0, 1, 3, 5, 7, 9, 11, 13, 15, 18]
	}
]

func get_level_count() -> int:
	return level_specs.size()

func get_level(index: int) -> Dictionary:
	var safe_index := clamp(index, 0, level_specs.size() - 1)
	var spec := level_specs[safe_index]
	var solution_path: Array[Vector2i] = []

	for coord: Vector2i in base_solution_path:
		solution_path.append(_transform_coord(coord, spec["rotation"], spec["mirror"]))

	if spec["reverse"]:
		solution_path.reverse()

	var number_points: Array[Dictionary] = []
	var checkpoints: Array = spec.get("checkpoints", CHECKPOINT_INDICES)
	for i in range(checkpoints.size()):
		number_points.append({
			"number": i + 1,
			"coord": solution_path[checkpoints[i]]
		})

	return {
		"index": safe_index,
		"title": spec["title"],
		"radius": 2,
		"number_points": number_points,
		"solution_path": solution_path
	}

func _transform_coord(coord: Vector2i, rotation_count: int, mirror: bool) -> Vector2i:
	var result := coord
	if mirror:
		result = Vector2i(-result.x - result.y, result.y)

	for i in range(rotation_count):
		result = Vector2i(-result.y, result.x + result.y)
	return result
