import numpy as np
from scipy import stats

emotion = np.array([4.004124340695277e-06-1.2956067317012907e-06, 1.5022015438913226e-06+2.804822291387912e-07])

normal = np.array([3.1065984953710082e-06+9.820178134211372e-07, 1.2282360084000212e-06+1.56786438022036e-08])

result = stats.ttest_rel(emotion,normal)

print(result)
