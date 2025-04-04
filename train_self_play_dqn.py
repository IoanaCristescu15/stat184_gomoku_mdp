import argparse
import numpy as np
import torch
import torch.optim as optim
from gomoku_env import GomokuEnvironment
from dqn_agent import DQNAgent



print("Script has started executing.") 



def train_dqn_self_play(
    num_episodes: int = 1000,
    board_size: int = 8,
    memory_size: int = 1000000,
    batch_size: int = 512,
    gamma: float = 0.99,
    epsilon_start: float = 1.0,
    epsilon_end: float = 0.0,
    epsilon_decay: float = 0.9995,
    learning_rate: float = 1e-3,
    update_target_every: int = 50,
    device: str = None,
    save_model_every: int = 100,
    model_save_path: str = "dqn_gomoku.pth",
    log_every: int = 20,
    config_path: str = "rewards/rewards_default.yml",
):
    """
    Trains two DQN agents through self-play in the Gomoku environment.
    """

    # Auto-detect device if not specified
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    device = torch.device(device)

    # Initialize environment and agents
    env = GomokuEnvironment(board_size=board_size, config_path=config_path)
    agent1 = DQNAgent(
        board_size=board_size,
        memory_size=memory_size,
        batch_size=batch_size,
        gamma=gamma,
        epsilon_start=epsilon_start,
        epsilon_end=epsilon_end,
        epsilon_decay=epsilon_decay,
        learning_rate=learning_rate,
        update_target_every=update_target_every,
        device=device,
    )

    agent2 = DQNAgent(
        board_size=board_size,
        memory_size=memory_size,
        batch_size=batch_size,
        gamma=gamma,
        epsilon_start=epsilon_start,
        epsilon_end=epsilon_end,
        epsilon_decay=epsilon_decay,
        learning_rate=learning_rate,
        update_target_every=update_target_every,
        device=device,
    )

    # Metrics for tracking performance
    agent1_wins = 0
    agent2_wins = 0
    draws = 0
    win_rates = []
    agent1_losses = []
    agent2_losses = []
    agent1_rewards_list = []
    agent2_rewards_list = []
    agent1_avg_losses = []
    agent2_avg_losses = []

    for episode in range(1, num_episodes + 1):
        state = env.reset()
        done = False
        agent1_reward = 0
        agent2_reward = 0
        step_count = 0

        # while not done:
        #     current_player = env.current_player
        #     if current_player == 1:
        #         agent = agent1
        #     else:
        #         agent = agent2

        #     # Agent selects an action from all possible actions
        #     action_index = agent.select_action(state)
        #     row, col = agent.action_index_to_coordinates(action_index)
        #     action = (row, col)

        #     # Execute action
        #     next_state, reward, done, info = env.step(action)

        #     # Print reward for valid action
        #     print(f"Episode {episode}, Step {step_count}, Player {current_player}, Action: {action}, Reward: {reward}")


        #     # Penalize invalid actions and prompt to try again until valid
        #     while info.get("info") == "Invalid move":
        #         # Store the transition with the penalty
        #         agent.store_transition(state, action_index, reward, next_state, done)
        #         if current_player == 1:
        #             agent1_reward += reward
        #         else:
        #             agent2_reward += reward

        #         # Print reward for invalid action
        #         print(f"Episode {episode}, Step {step_count}, Player {current_player}, Invalid Action: {action}, Reward: {reward}")

        #         # Agent selects another action
        #         action_index = agent.select_action(state)
        #         row, col = agent.action_index_to_coordinates(action_index)
        #         action = (row, col)

        #         # Execute the new action
        #         next_state, reward, done, info = env.step(action)

        #     # Store the valid transition
        #     agent.store_transition(state, action_index, reward, next_state, done)

        #     # Track rewards for each agent
        #     if current_player == 1:
        #         agent1_reward += reward
        #     else:
        #         agent2_reward += reward

        #     # Update the agent
        #     loss = agent.update_model()
        #     if loss is not None:
        #         if current_player == 1:
        #             agent1_losses.append(loss)
        #         else:
        #             agent2_losses.append(loss)

        #     # Prepare for next step
        #     state = next_state
        #     step_count += 1

        while not done:
            current_player = env.current_player
            if current_player == 1:
                agent = agent1
            else:
                agent = agent2

            # Get valid moves from the environment
            valid_moves = env.get_valid_moves()
            # Agent selects an action from valid moves
            action_index = agent.select_action(state, valid_moves)
            row, col = agent.action_index_to_coordinates(action_index)
            action = (row, col)

            # Execute action
            next_state, reward, done, info = env.step(action)

            # Store the transition
            agent.store_transition(state, action_index, reward, next_state, done)

            # Track rewards for each agent
            if current_player == 1:
                agent1_reward += reward
            else:
                agent2_reward += reward

            # Update the agent
            loss = agent.update_model()
            if loss is not None:
                if current_player == 1:
                    agent1_losses.append(loss)
                else:
                    agent2_losses.append(loss)

            # Prepare for next step
            state = next_state
            step_count += 1


            if done:
                if 'info' in info:
                    #print(f"Episode {episode}, {info['info']}")
                    if f"Player 1 wins" in info["info"]:
                        agent1_wins += 1
                        agent2_reward -= 1  # Penalize Agent 2
                    elif f"Player 2 wins" in info["info"]:
                        agent2_wins += 1
                        agent1_reward -= 1  # Penalize Agent 1
                    elif "Draw" in info["info"]:
                        draws += 1
                break  

        # Update target networks periodically
        if episode % agent1.update_target_every == 0:
            agent1.update_target_network()
            agent2.update_target_network()

        # Log metrics
        agent1_rewards_list.append(agent1_reward)
        agent2_rewards_list.append(agent2_reward)
        avg_agent1_loss = np.mean(agent1_losses[-step_count:]) if agent1_losses else 0
        avg_agent2_loss = np.mean(agent2_losses[-step_count:]) if agent2_losses else 0
        agent1_avg_losses.append(avg_agent1_loss)
        agent2_avg_losses.append(avg_agent2_loss)

        total_games = agent1_wins + agent2_wins + draws
        agent1_win_rate = agent1_wins / total_games if total_games > 0 else 0
        agent2_win_rate = agent2_wins / total_games if total_games > 0 else 0
        win_rates.append((agent1_win_rate, agent2_win_rate))

        if episode % log_every == 0:
            # Print progress
            print(f"Episode {episode}, Agent1 Reward: {agent1_reward}, Agent2 Reward: {agent2_reward}, "
                  f"Agent1 Win Rate: {agent1_win_rate:.2f}, Agent2 Win Rate: {agent2_win_rate:.2f}, "
                  f"Agent1 Avg Loss: {avg_agent1_loss:.4f}, Agent2 Avg Loss: {avg_agent2_loss:.4f}, "
                  f"Epsilon: {agent1.epsilon:.4f}")
            #env.render()

    # Save the final models
    agent1.save_model(f"agent1_{model_save_path}")
    agent2.save_model(f"agent2_{model_save_path}")
    print("Training completed and models saved.")

    # Save metrics for plotting
    np.save("win_rates.npy", win_rates)
    np.save("agent1_rewards.npy", agent1_rewards_list)
    np.save("agent2_rewards.npy", agent2_rewards_list)
    np.save("agent1_losses.npy", agent1_avg_losses)
    np.save("agent2_losses.npy", agent2_avg_losses)
    print("Training metrics saved!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train DQN Agents via Self-Play in Gomoku")
    parser.add_argument("--num_episodes", type=int, default=1000, help="Number of training episodes")
    parser.add_argument("--board_size", type=int, default=8, help="Size of the Gomoku board")
    parser.add_argument("--config_name", type=str, default="rewards_default", help="Name of the reward configuration file (without .yml extension)")
    parser.add_argument("--device", type=str, default=None, help="Device to use for computations ('cpu' or 'cuda'). If not specified, auto-detects.")
    parser.add_argument("--model_save_path", type=str, default="dqn_gomoku.pth", help="Path to save the model")
    args = parser.parse_args()

    config_path = f"rewards/{args.config_name}.yml"

    train_dqn_self_play(
        num_episodes=args.num_episodes,
        board_size=args.board_size,
        device=args.device,
        model_save_path=args.model_save_path,
        config_path=config_path,
    )



# Notes
# --device takes arguments cpu or cuda
# --config_name takes arguments rewards_default, rewards_1, rewards_2
# --num_episodes takes any integer value