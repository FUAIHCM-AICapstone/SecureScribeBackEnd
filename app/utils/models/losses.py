import torch
import torch.nn as nn


class LossCTC(nn.Module):
    def __init__(self):
        super(LossCTC, self).__init__()

        # CTC Loss
        self.loss = nn.CTCLoss(blank=0, reduction="none", zero_infinity=True)

    def forward(self, batch, pred):
        # Unpack Batch
        x, y, x_len, y_len = batch

        # Unpack Predictions
        outputs_pred, f_len, _ = pred

        # Compute Loss
        loss = self.loss(
            log_probs=torch.nn.functional.log_softmax(outputs_pred, dim=-1).transpose(
                0, 1
            ),
            targets=y,
            input_lengths=f_len,
            target_lengths=y_len,
        ).mean()

        return loss


class LossInterCTC(nn.Module):
    def __init__(self, interctc_lambda):
        super(LossInterCTC, self).__init__()

        # CTC Loss
        self.loss = nn.CTCLoss(blank=0, reduction="none", zero_infinity=False)

        # InterCTC Lambda
        self.interctc_lambda = interctc_lambda

    def forward(self, batch, pred):
        # Unpack Batch
        x, y, x_len, y_len = batch

        # Unpack Predictions
        outputs_pred, f_len, _, interctc_probs = pred

        # Compute CTC Loss
        loss_ctc = self.loss(
            log_probs=torch.nn.functional.log_softmax(outputs_pred, dim=-1).transpose(
                0, 1
            ),
            targets=y,
            input_lengths=f_len,
            target_lengths=y_len,
        )

        # Compute Inter Loss
        loss_inter = sum(
            self.loss(
                log_probs=interctc_prob.log().transpose(0, 1),
                targets=y,
                input_lengths=f_len,
                target_lengths=y_len,
            )
            for interctc_prob in interctc_probs
        ) / len(interctc_probs)

        # Compute total Loss
        loss = (1 - self.interctc_lambda) * loss_ctc + self.interctc_lambda * loss_inter
        loss = loss.mean()

        return loss


class LossCE(nn.Module):
    def __init__(self):
        super(LossCE, self).__init__()

        # CE Loss
        self.loss = nn.CrossEntropyLoss(
            weight=None,
            size_average=None,
            ignore_index=-1,
            reduce=None,
            reduction="mean",
        )

    def forward(self, batch, pred):
        # Unpack Batch
        x, x_len, y = batch

        # Unpack Predictions
        outputs_pred = pred

        # Compute Loss
        loss = self.loss(input=outputs_pred.transpose(1, 2), target=y)

        return loss
