extends Resource
class_name LevelData

# Grid size for this puzzle.
@export var grid_size: int = 5

# Dot pairs in the format:
# [
#   {"color": Color, "start": Vector2i, "end": Vector2i},
# ]
@export var dot_pairs: Array[Dictionary] = [
	{
		"color": Color(1, 0.3, 0.3),
		"start": Vector2i(0, 0),
		"end": Vector2i(4, 1)
	},
	{
		"color": Color(0.3, 0.6, 1.0),
		"start": Vector2i(1, 4),
		"end": Vector2i(4, 4)
	}
]
