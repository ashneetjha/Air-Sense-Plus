from __future__ import annotations

import torch
from torch import nn


class AttentionLayer(nn.Module):
    def __init__(self, hidden_size: int) -> None:
        super().__init__()
        self.score = nn.Linear(hidden_size, 1)

    def forward(self, sequence_output: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        attn_logits = self.score(sequence_output).squeeze(-1)
        weights = torch.softmax(attn_logits, dim=1)
        context = torch.sum(sequence_output * weights.unsqueeze(-1), dim=1)
        return context, weights


class LSTMAttentionRegressor(nn.Module):
    def __init__(self, input_size: int, hidden_size: int = 64) -> None:
        super().__init__()
        self.lstm = nn.LSTM(input_size=input_size, hidden_size=hidden_size, batch_first=True)
        self.attention = AttentionLayer(hidden_size)
        self.output = nn.Linear(hidden_size, 1)

    def forward(self, inputs: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        sequence_output, _ = self.lstm(inputs)
        context, weights = self.attention(sequence_output)
        return self.output(context), weights
