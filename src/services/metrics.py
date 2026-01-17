"""Metrics calculation functions (WER, CER).

Validates: Requirements 9.5
"""


def calculate_wer(hypothesis: str, reference: str) -> float:
    """Calculate Word Error Rate (WER).
    
    WER = (S + D + I) / N
    where:
    - S = substitutions
    - D = deletions
    - I = insertions
    - N = number of words in reference
    
    Validates: Requirements 9.5
    """
    ref_words = reference.lower().split()
    hyp_words = hypothesis.lower().split()
    
    if len(ref_words) == 0:
        return 0.0 if len(hyp_words) == 0 else 1.0
    
    # Dynamic programming for edit distance
    d = [[0] * (len(hyp_words) + 1) for _ in range(len(ref_words) + 1)]
    
    for i in range(len(ref_words) + 1):
        d[i][0] = i
    for j in range(len(hyp_words) + 1):
        d[0][j] = j
    
    for i in range(1, len(ref_words) + 1):
        for j in range(1, len(hyp_words) + 1):
            if ref_words[i - 1] == hyp_words[j - 1]:
                d[i][j] = d[i - 1][j - 1]
            else:
                d[i][j] = min(
                    d[i - 1][j] + 1,      # deletion
                    d[i][j - 1] + 1,      # insertion
                    d[i - 1][j - 1] + 1,  # substitution
                )
    
    return d[len(ref_words)][len(hyp_words)] / len(ref_words)


def calculate_cer(hypothesis: str, reference: str) -> float:
    """Calculate Character Error Rate (CER).
    
    CER = (S + D + I) / N
    where operations are at character level.
    
    Validates: Requirements 9.5
    """
    ref_chars = list(reference.lower())
    hyp_chars = list(hypothesis.lower())
    
    if len(ref_chars) == 0:
        return 0.0 if len(hyp_chars) == 0 else 1.0
    
    # Dynamic programming for edit distance
    d = [[0] * (len(hyp_chars) + 1) for _ in range(len(ref_chars) + 1)]
    
    for i in range(len(ref_chars) + 1):
        d[i][0] = i
    for j in range(len(hyp_chars) + 1):
        d[0][j] = j
    
    for i in range(1, len(ref_chars) + 1):
        for j in range(1, len(hyp_chars) + 1):
            if ref_chars[i - 1] == hyp_chars[j - 1]:
                d[i][j] = d[i - 1][j - 1]
            else:
                d[i][j] = min(
                    d[i - 1][j] + 1,
                    d[i][j - 1] + 1,
                    d[i - 1][j - 1] + 1,
                )
    
    return d[len(ref_chars)][len(hyp_chars)] / len(ref_chars)
