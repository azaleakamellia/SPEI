import logging
from calendar import isleap
from typing import List, Optional, Tuple, Union

from numpy import array, std
from pandas import (
    DataFrame,
    DatetimeIndex,
    Grouper,
    Index,
    Series,
    concat,
    infer_freq,
    to_datetime,
)
from scipy.stats import (
    fisk,
    gamma,
    genextreme,
    genlogistic,
    kstest,
    logistic,
    lognorm,
    norm,
    pearson3,
)

from ._typing import ContinuousDist, NDArrayFloat


def validate_series(series: Series) -> Series:
    series = series.copy()

    if not isinstance(series, Series):
        if isinstance(series, DataFrame):
            if len(series.columns) == 1:
                logging.warning(
                    "Please convert series of type pandas.DataFrame to a"
                    "pandas.Series using DataFrame.squeeze(). Now done automatically."
                )
                series = series.squeeze()
            else:
                raise TypeError(
                    "Please provide a pandas.Series instead of a pandas.DataFrame"
                )
        else:
            raise TypeError(f"Please provide a Pandas Series instead of {type(series)}")

    return series


def validate_index(index: Index) -> DatetimeIndex:
    index = index.copy()

    if not isinstance(index, DatetimeIndex):
        logging.info(
            f"Expected the index to be a DatetimeIndex. Automatically converted "
            f"{type(index)} using pd.to_datetime(Index)"
        )
        index = DatetimeIndex(to_datetime(index))

    return index


def infer_frequency(index: DatetimeIndex) -> str:
    """Infer frequency"""
    inf_freq = infer_freq(index)
    if inf_freq is None:
        logging.info("Could not infer frequency from index, using monthly frequency")
        inf_freq = "M"
    return inf_freq


def group_yearly_df(series: Series) -> DataFrame:
    strfstr: str = "%m-%d %H:%M:%S"
    grs = {}
    for year, gry in series.groupby(Grouper(freq="Y")):
        gry.index = to_datetime(
            "2000-" + gry.index.strftime(strfstr), format="%Y-" + strfstr
        )
        grs[year.year] = gry
    return concat(grs, axis=1)


def get_data_series(group_df: DataFrame) -> Series:
    strfstr: str = "%m-%d %H:%M:%S"

    idx = array(
        [
            (f"{col}-" + group_df.index.strftime(strfstr)).tolist()
            for col in group_df.columns
        ]
    ).flatten()
    # remove illegal 29 febraury for non leap years created by group_yearly_df
    boolidx = ~array(
        [
            (x.split(" ")[0].split("-", 1)[1] == "02-29")
            and not isleap(int(x.split(" ")[0].split("-")[0]))
            for x in idx
        ]
    )

    dt_idx = to_datetime(idx[boolidx], format="%Y-" + strfstr)
    values = group_df.transpose().values.flatten()[boolidx]
    return Series(values, index=dt_idx).dropna()


def dist_test(
    series: Union[Series, NDArrayFloat],
    dist: ContinuousDist,
    N: int = 100,
    alpha: float = 0.05,
) -> Tuple[str, float, bool, tuple]:
    """Fit a distribution and perform the two-sided
    Kolmogorov-Smirnov test for goodness of fit. The
    null hypothesis is that the data and distributions
    are identical, the alternative is that they are
    not identical. [scipy_2021]_

    Parameters
    ----------
    data : Union[Series, NDArray[float]]
        pandas Series or numpy array of floats of observations of random
        variables
    dist: scipy.stats.rv_continuous
        Can be any continuous distribution from the
        scipy.stats library.
    N : int, optional
        Sample size, by default 100
    alpha : float, optional
        Significance level for testing, default is 0.05
        which is equal to a a confidence level of 95%;
        that is, the null hypothesis will be rejected in
        favor of the alternative if the p-value is
        less than 0.05.

    Returns
    -------
    string, float, bool, tuple
        distribution name, p-value and fitted parameters

    References
    -------
    .. [scipy_2021] Onnen, H.: Intro to Probability
     Distributions and Distribution Fitting with Pythons
    SciPy, 2021.
    """
    fitted = dist.fit(series, scale=std(series))
    dist_name = getattr(dist, "name")
    ks = kstest(series, dist_name, fitted, N=N)[1]
    rej_h0 = ks < alpha
    return dist_name, ks, rej_h0, fitted


def dists_test(
    series: Union[Series, NDArrayFloat],
    distributions: Optional[List[ContinuousDist]] = None,
    N: int = 100,
    alpha: float = 0.05,
) -> DataFrame:
    """Fit a list of distribution and perform the
    two-sided Kolmogorov-Smirnov test for goodness
    of fit. The null hypothesis is that the data and
    distributions are identical, the alternative is
    that they are not identical. [scipy_2021]_

    Parameters
    ----------
    series : Union[Series, NDArray[float]]
        pandas Series with observations of random variables
    distributions : list of scipy.stats.rv_continuous, optional
        A list of (can be) any continuous distribution from the scipy.stats
        library, by default None which makes a custom selection
    N : int, optional
        Sample size, by default 100
    alpha : float, optional
        Significance level for testing, default is 0.05
        which is equal to a a confidence level of 95%;
        that is, the null hypothesis will be rejected in
        favor of the alternative if the p-value is
        less than 0.05.

    Returns
    -------
    pandas.DataFrame
        DataFrame with the distribution names,
        pvalues and parameters

    References
    -------
    .. [scipy_2021] Onnen, H.: Intro to Probability
     Distributions and Distribution Fitting with Pythons
    SciPy, 2021.
    """
    if distributions is None:
        distributions = [
            norm,
            gamma,
            genextreme,
            pearson3,
            fisk,
            lognorm,
            logistic,
            genlogistic,
        ]

    df = DataFrame([dist_test(series, D, N, alpha) for D in distributions])
    cols = ["Distribution", "KS p-value", "Reject H0"]
    cols += [f"Param {i+1}" for i in range(len(df.columns) - len(cols))]
    df = df.rename(columns=dict(zip(df.columns, cols))).set_index(cols[0])
    df["Dist"] = distributions

    return df
