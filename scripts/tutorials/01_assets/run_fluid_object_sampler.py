# Based on the run_rigid_object.py script

"""
This script demonstrates how to create a rigid object and interact with it.

.. code-block:: bash

    # Usage
    ./isaaclab.sh -p scripts/tutorials/01_assets/run_fluid_object.py

"""

"""Launch Isaac Sim Simulator first."""


import argparse

from isaaclab.app import AppLauncher

# add argparse arguments
parser = argparse.ArgumentParser(description="Tutorial on spawning and interacting with a rigid object.")
# append AppLauncher cli args
AppLauncher.add_app_launcher_args(parser)
# parse the arguments
args_cli = parser.parse_args()

# launch omniverse app
app_launcher = AppLauncher(args_cli)
simulation_app = app_launcher.app

"""Rest everything follows."""

import torch

import isaaclab.sim as sim_utils
import isaaclab.utils.math as math_utils
from isaaclab.assets import FluidObject, FluidObjectCfg
from isaaclab.sim import SimulationContext


def design_scene():
    """Designs the scene."""
    # Ground-plane
    cfg = sim_utils.GroundPlaneCfg()
    cfg.func("/World/defaultGroundPlane", cfg)
    # Lights
    cfg = sim_utils.DomeLightCfg(intensity=2000.0, color=(0.8, 0.8, 0.8))
    cfg.func("/World/Light", cfg)

    # Create separate groups called "Origin1", "Origin2", "Origin3"
    # Each group will have fluid in it
    origins = [[0.0, 0.0, 1.0], [0.5, 0.0, 1.0], [0.0, 0.5, 1.0], [0.5, 0.5, 1.0]]
    for i, origin in enumerate(origins):
        sim_utils.create_prim(f"/World/Origin_{i}", "Xform", translation=origin)

    # Fluid Object
    fluid_cfg = FluidObjectCfg(
        prim_path = "/World/Origin_.*",
        sampled_shape = "cylinder", # Base isaac sim prims like "cylinder", "cube", "sphere" can be used for sampling the fluid
        num_envs = len(origins), # Number of environments,
        scale_x = 0.2, # Sampled prim scale along x-axis
        scale_y = 0.2, # Sampled prim scale along y-axis
        scale_z = 0.4, # Sampled prim scale along z-axis
        particle_mass = 0.001,
        density = 0.0,
        viscosity = 0.1,
        cohesion = 5.0,
        surface_tension = 0.02,
        friction = 1.0,
        damping = 0.9,
        hidden_particles = True,
        anisotropy = True,
        smoothing = True,
        isosurface = True,
        transparency = True,
        particleSpacing = 0.01,
    )
    fluid_object = FluidObject(cfg=fluid_cfg)

    # Spawn the fluid in the three origins
    # NOTE: if the environments are replicated like during RL, it is sufficient to spawn the fluid only in the first environment
    for i, origin in enumerate(origins):
        fluid_object.spawn_fluid_sampler(env_id=i, pos=origin)

    # return the scene information
    scene_entities = {"fluid": fluid_object}
    return scene_entities, origins


def run_simulator(sim: sim_utils.SimulationContext, entities: dict[str, FluidObject], origins: torch.Tensor):
    """Runs the simulation loop."""
    # Extract scene entities
    # note: we only do this here for readability. In general, it is better to access the entities directly from
    #   the dictionary. This dictionary is replaced by the InteractiveScene class in the next tutorial.
    fluid_object = entities["fluid"]
    # Define simulation stepping
    sim_dt = sim.get_physics_dt()
    sim_time = 0.0
    count = 0
    
    # Simulate physics
    while simulation_app.is_running():                
        # reset
        if count % 250 == 0:
            # reset counters
            sim_time = 0.0
            count = 0
            # Set internal base values for the fluid (it only runs the first time)
            fluid_object.initialize_fluid_data(base_env_origin = origins[0])
            # Create random translations for the reset position
            offset = torch.randn(len(origins), 1, 3).cuda()*0.1
            reset_particle_pos = fluid_object.initial_particles_pos + offset
            # Reset the fluid position (no argument resets it to base stored values)
            fluid_object.set_particles_pos_and_vel(particles_pos = reset_particle_pos)

            print("----------------------------------------")
            print("[INFO]: Resetting object state...")

        # perform step
        sim.step()
        # update sim-time
        sim_time += sim_dt
        count += 1
        # get the particles positions and velocities
        if count % 50 == 0:
            particle_positions = fluid_object.get_particles_pos()
            particle_velocities = fluid_object.get_particles_vel()



def main():
    """Main function."""
    # Load kit helper
    sim_cfg = sim_utils.SimulationCfg(device=args_cli.device, use_fabric=False) # IMPORTANT: disable fabric
    sim = SimulationContext(sim_cfg)
    # Set main camera
    sim.set_camera_view(eye=[1.5, 0.0, 1.0], target=[0.0, 0.0, 0.0])
    # Design scene
    scene_entities, scene_origins = design_scene()
    scene_origins = torch.tensor(scene_origins, device=sim.device)
    # Play the simulator
    sim.reset()
    # Now we are ready!
    print("[INFO]: Setup complete...")
    # Run the simulator
    run_simulator(sim, scene_entities, scene_origins)


if __name__ == "__main__":
    # run the main function
    main()
    # close sim app
    simulation_app.close()