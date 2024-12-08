import argparse
import numpy as np
import torch
import os
import torch.optim as optim
from gomoku_env import GomokuEnvironment
from dqn_agent import DQNAgent
from utils import smartest_rule_based_move

print("Script has started executing.") 


def train_dqn_rule_based(
    num_episodes: int = 1000,
    board_size: int = 15,
    memory_size: int = 10000000,
    batch_size: int = 512,
    gamma: float = 0.95,
    epsilon_start: float = 1.0,
    epsilon_end: float = 0.0,
    epsilon_decay: float = 0.9995,
    learning_rate: float = 1e-3,
    update_target_every: int = 10,
    device: str = None,
    save_model_every: int = 100,
    model_save_path: str = "dqn_gomoku.pth",
    log_every: int = 10,
    rewards_type: str = "rewards_default",
):
    """
    Trains a DQN agent against rule based agent in the Gomoku environment.
    """

    config_path = f"rewards/{rewards_type}.yml"

    # Auto-detect device if not specified
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"
    device = torch.device(device)

    # Initialize environment and DQN agent
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

    # Metrics for tracking performance
    agent1_wins = 0
    rule_based_wins = 0
    draws = 0
    win_rates = []
    agent1_losses = []
    agent1_rewards_list = []
    agent1_avg_losses = []

    for episode in range(1, num_episodes + 1):
        state = env.reset()
        done = False
        agent1_reward = 0
        step_count = 0

        while not done:
            current_player = env.current_player
            if current_player == 1:
                # Agent 1's turn (DQN agent)
                valid_moves = env.get_valid_moves()
                action_index = agent1.select_action(state, valid_moves)
                row, col = agent1.action_index_to_coordinates(action_index)
                action = (row, col)
            else:
                # Rule-based player's turn
                action = smartest_rule_based_move(env)

            # Execute action
            next_state, reward, done, info = env.step(action)

            if current_player == 1:
                # Store the transition and update model for Agent 1
                agent1.store_transition(state, action_index, reward, next_state, done)
                agent1_reward += reward
                loss = agent1.update_model()
                if loss is not None:
                    agent1_losses.append(loss)


            if done:
                if 'info' in info:
                    #print(f"Episode {episode}, {info['info']}")
                    if f"Player 1 wins" in info["info"]:
                        agent1_wins += 1
                    elif f"Player 2 wins" in info["info"]:
                        rule_based_wins += 1
                        agent1_reward -= 1  # Penalize Agent 1
                    elif "Draw" in info["info"]:
                        draws += 1
                break  # End the game

        # Update target network periodically
        if episode % agent1.update_target_every == 0:
            agent1.update_target_network()
        
        # Log metrics
        agent1_rewards_list.append(round(agent1_reward, 1))
        avg_agent1_loss = np.mean(agent1_losses[-step_count:]) if agent1_losses else 0
        agent1_avg_losses.append(avg_agent1_loss)

        total_games = agent1_wins + rule_based_wins + draws
        agent1_win_rate = agent1_wins / total_games if total_games > 0 else 0
        rule_based_win_rate = rule_based_wins / total_games if total_games > 0 else 0
        win_rates.append((agent1_win_rate, rule_based_win_rate))

        if episode % log_every == 0:
            print(f"Episode {episode}, Agent1 Reward: {agent1_reward}, "
                  f"Agent1 Win Rate: {agent1_win_rate:.2f}, Rule-Based Win Rate: {rule_based_win_rate:.2f}, "
                  f"Agent1 Avg Loss: {avg_agent1_loss:.4f}, Epsilon: {agent1.epsilon:.4f}")
            env.render()
    
    folder = "rule_based_dqn"
    # Save the plot as an image
    if not os.path.exists(f"{folder}/{rewards_type}"):
        os.makedirs(f"{folder}/{rewards_type}")

    # Save the final model
    agent1.save_model(f"{folder}/{rewards_type}/{model_save_path}")
    print("Training completed and model saved.")

    # Save metrics for plotting
    np.save(f"{folder}/{rewards_type}/win_rates.npy", win_rates)
    np.save(f"{folder}/{rewards_type}/agent1_rewards.npy", agent1_rewards_list)
    np.save(f"{folder}/{rewards_type}/agent1_losses.npy", agent1_avg_losses)
    print("Training metrics saved!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train DQN Agents against Rule-based Agent in Gomoku")
    parser.add_argument("--num_episodes", type=int, default=1000, help="Number of training episodes")
    parser.add_argument("--board_size", type=int, default=15, help="Size of the Gomoku board")
    parser.add_argument("--config_name", type=str, default="rewards_default", help="Name of the reward configuration file (without .yml extension)")
    parser.add_argument("--device", type=str, default=None, help="Device to use for computations ('cpu' or 'cuda'). If not specified, auto-detects.")
    parser.add_argument("--model_save_path", type=str, default="dqn_gomoku.pth", help="Path to save the model")
    args = parser.parse_args()

    # config_path = f"rewards/{args.config_name}.yml"

    train_dqn_rule_based(
        num_episodes=args.num_episodes,
        board_size=args.board_size,
        device=args.device,
        model_save_path=args.model_save_path,
        rewards_type=args.config_name,
    )