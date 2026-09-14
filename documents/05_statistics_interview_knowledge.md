# Statistics Mock Interview Knowledge

## Core Questions
1. What is a hypothesis? Difference between null and alternative hypotheses?
2. Difference between correlation and covariance?
3. What is a chi-square test and when is it used?
4. What is the Central Limit Theorem and why is it important?
5. What does standard deviation tell us?
6. Difference between descriptive and inferential statistics?
7. What do skewness and kurtosis tell us?
8. Properties of a normal distribution?
9. What is ANOVA and when is it preferred to multiple t-tests?
10. What is a p-value and how is it used?
11. What are the three measures of central tendency? When prefer median?
12. What is probability and why is it important?
13. How choose between a Z-test and T-test?
14. Given exam scores of 500 students, what statistics would you calculate before reporting/modeling?
15. How would sampling estimate customer satisfaction? Which sampling method?
16. What are Type I and Type II errors?
17. What are outliers and how should they be handled?
18. Retail company: satisfaction differs across four stores. Which statistical test?

## Interview Answer Principles

### Hypothesis
- H0: no significant effect/difference/relationship.
- H1/Ha: significant effect/difference/relationship.
- Use sample data and a statistical test to make a decision.
- Prefer saying “fail to reject H0” rather than “accept H0.”

### Correlation vs Covariance
- Covariance indicates direction of joint movement and is scale-dependent.
- Correlation indicates direction and strength of a linear relationship and is standardized from -1 to +1.
- Correlation does not imply causation.

Python:
```python
import numpy as np

np.cov(x, y)
np.corrcoef(x, y)[0, 1]
```

### Chi-Square
- Used mainly with categorical data.
- Independence test: whether two categorical variables are associated.
- Goodness-of-fit: whether observed frequencies match expected frequencies.

Python:
```python
from scipy.stats import chi2_contingency

chi2, p, dof, expected = chi2_contingency(table)
```

### Central Limit Theorem
- With sufficiently large random samples, the sampling distribution of the sample mean tends toward a normal distribution even when the population itself is not normal.
- Important for confidence intervals, hypothesis testing and inference.
- It does not mean the original dataset becomes normal.

### Standard Deviation
- Measures spread around the mean.
- Low SD: values are relatively clustered.
- High SD: values are more dispersed.

Python:
```python
import numpy as np

np.std(data)              # population-style calculation
np.std(data, ddof=1)      # sample standard deviation
```

### Descriptive vs Inferential
- Descriptive: summarize observed data.
- Inferential: use sample data to draw conclusions about a population.

Examples:
- Mean, median, SD, quartiles, charts → descriptive.
- Confidence intervals, hypothesis tests, ANOVA, regression inference → inferential.

### Skewness and Kurtosis
- Skewness measures asymmetry.
- Positive skew: longer right tail.
- Negative skew: longer left tail.
- Kurtosis describes tail heaviness/extreme-value behavior; software conventions can differ.

Python:
```python
from scipy.stats import skew, kurtosis

skew(data)
kurtosis(data)
```

### Normal Distribution
Key properties:
- Continuous
- Bell-shaped
- Symmetric
- Mean = median = mode
- Total area = 1
- Defined by mean and standard deviation
- Approximately 68%, 95%, and 99.7% within 1, 2, and 3 standard deviations respectively.

### ANOVA
- Used to compare means across three or more groups.
- H0: all group means are equal.
- H1: at least one group mean differs.
- Avoids the inflated Type I error associated with many pairwise t-tests.
- If significant, use a post-hoc test such as Tukey HSD to identify which groups differ.

Python:
```python
from scipy.stats import f_oneway

f_stat, p = f_oneway(group1, group2, group3, group4)
```

### P-value
- Probability of obtaining a result at least as extreme as the observed result, assuming H0 is true.
- If p < alpha (commonly 0.05), reject H0.
- If p >= alpha, fail to reject H0.
- A p-value is not the probability that H0 is true.
- Statistical significance does not automatically mean practical significance.

### Central Tendency
- Mean: arithmetic average.
- Median: middle value after sorting.
- Mode: most frequent value.
- Median is preferred for skewed data or data with strong outliers.

### Probability
- Quantifies uncertainty and ranges from 0 to 1.
- Important for risk, prediction, decision-making and statistical inference.

### Z-test vs T-test
Consider:
- Whether population standard deviation is known.
- Sample size.
- Distribution/assumptions.
- Type of comparison.

Typical rule:
- Z-test when population sigma is known or under appropriate large-sample conditions.
- T-test when population sigma is unknown, especially with smaller samples.

### 500 Exam Scores: Initial Analysis
Before modeling:
1. Check data quality.
2. Check missing values and duplicates.
3. Calculate mean, median, mode.
4. Calculate range, variance, SD, IQR.
5. Calculate quartiles and percentiles.
6. Examine skewness and kurtosis.
7. Detect and investigate outliers.
8. Plot histogram and boxplot.
9. Examine relationships with relevant variables.

Useful Python:
```python
df["score"].describe()
df["score"].isna().sum()
df["score"].mean()
df["score"].median()
df["score"].std()
df["score"].skew()
df["score"].kurt()
```

### Sampling
- Census: survey the entire population.
- Sample: representative subset of the population.
- Simple random sampling: useful when the population is reasonably homogeneous and a sampling frame exists.
- Stratified sampling: useful when important subgroups need representation.
- Systematic, cluster and convenience sampling are other approaches.

### Type I vs Type II
- Type I error: reject a true H0 → false positive.
- Type II error: fail to reject a false H0 → false negative.
- Alpha controls the chosen significance threshold for Type I error.

### Outliers
Do not automatically delete outliers.
Investigate whether they are:
- Data-entry errors
- Measurement errors
- Fraud/anomalies
- Genuine rare observations

IQR method:
```python
Q1 = df["value"].quantile(0.25)
Q3 = df["value"].quantile(0.75)
IQR = Q3 - Q1

lower = Q1 - 1.5 * IQR
upper = Q3 + 1.5 * IQR

outliers = df[(df["value"] < lower) | (df["value"] > upper)]
```

Possible handling:
- Correct erroneous records.
- Remove only when justified.
- Retain genuine observations.
- Transform data.
- Winsorize/cap when appropriate.
- Use robust statistical methods when suitable.

### Four Store Locations
For four independent stores with numerical satisfaction scores:
- Recommended test: one-way ANOVA.
- H0: all four mean satisfaction scores are equal.
- H1: at least one differs.
- If significant, use Tukey HSD for pairwise identification.

## Fast Test-Selection Framework
When unsure:
1. What type of data do I have?
2. What is my objective?
3. How many groups/variables are involved?
4. Are the groups independent or paired?
5. What assumptions apply?
6. Which test matches the design?
7. What does the p-value mean in this context?
