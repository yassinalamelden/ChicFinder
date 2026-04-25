import torch
import torch.nn.functional as F

class InfoNCELoss(torch.nn.Module):
    def __init__(self, temperature=0.07):
        super().__init__()
        self.temperature = temperature
    
    def forward(self, anchor, positive, negative):
        # Normalize embeddings to calculate cosine similarity
        anchor = F.normalize(anchor, dim=-1)
        positive = F.normalize(positive, dim=-1)
        negative = F.normalize(negative, dim=-1)
        
        # Positive similarity: (batch_size, 1)
        pos_sim = torch.sum(anchor * positive, dim=-1, keepdim=True)
        
        # Negative similarity against ALL negatives in the batch: (batch_size, batch_size)
        neg_sim = torch.mm(anchor, negative.T)
        
        # Combine them
        logits = torch.cat([pos_sim, neg_sim], dim=1) / self.temperature
        
        # Force labels to be a strictly 1D tensor of integers
        labels = torch.zeros(logits.size(0), dtype=torch.long, device=logits.device)
        
        return F.cross_entropy(logits, labels)