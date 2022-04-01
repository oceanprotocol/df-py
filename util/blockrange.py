from enforce_typing import enforce_types
import numpy

@enforce_types
class BlockRange:
    def __init__(self, start_block:int, end_block:int, num_samples:int,
                 random_seed=None):
        assert start_block > 0
        assert end_block > 0
        assert num_samples >= 0
        assert start_block <= end_block
        cand_blocks = list(range(start_block, end_block+1))
        num_samples = min(num_samples, len(cand_blocks))
        if random_seed is not None:
            numpy.random.seed(random_seed)
        self._range = sorted(numpy.random.choice(cand_blocks, num_samples, replace=False))
        
        self.start_block:int = start_block
        self.end_block:int = end_block

    def getRange(self) -> list:
        return self._range

    def numBlocks(self) -> int:
        return len(self.getRange())

    def __str__(self):
        return f"BlockRange: start_block={self.start_block}" \
            f", end_block={self.end_block}" \
            f", # blocks sampled={self.numBlocks()}" \
            f", range={self.getRange()[:4]}.."
