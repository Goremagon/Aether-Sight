# Protocol Nyx - Project Context

## Project Overview
Protocol Nyx is a top-down space RTS/Shooter featuring "Sentinels"—autonomous ships that use flocking behavior to swarm and attack "Eldritch" biological horrors.

## Directory Structure
- `Assets/Scripts/`: Core source code.
  - `AI/`: Generic AI tools (`BoidUnit`, `StateMachine`, `FlockingBehavior`).
  - `Sentinels/`: Specific implementation (`SentinelBase`, `SentinelStates`).
  - `Gameplay/`: Combat interfaces (`IDamageable`), Unit logic.
  - `Settings/`: Input actions, Renderer settings.
- `Assets/Settings/Blueprints/`: Prefabs for Bullets, Enemies, and Sentinels.

## Current System Status

### 1. Sentinel AI [Status: FUNCTIONAL]
- **Movement**: Uses Boid algorithm (Separation, Alignment, Cohesion).
- **Decision Making**: Finite State Machine (Idle -> Chase -> Attack).
- **Files**: `SentinelBase.cs`, `SentinelStates.cs`, `BoidUnit.cs`, `FlockingBehavior.cs`.

### 2. Player System [Status: IN PROGRESS]
- **Control**: WASD/Joystick movement via `InputManager`.
- **Health**: `PlayerHealth.cs` manages damage states.
- **Combat**: Basic projectile firing.

### 3. Enemy System [Status: PROTOTYPE]
- **Logic**: Basic chase logic in `EnemyAI.cs`.
- **Spawning**: `EnemySpawner.cs` handles wave generation.
- **Targeting**: Enemies currently target the Player; Sentinels target "Eldritch" tag.

## Immediate Goals
1. Implement damage logic for Sentinels (they can move but cannot yet kill or die).
2. Create a "Director" for dynamic difficulty (Eldritch spawns).
3. Refine the Mining/Resource loop (currently non-existent).