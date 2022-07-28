# SPEI
A simple Python package to calculate drought indices such as the SPI, SPEI and SGI. There are other great packages available to calculate these indices but they are either written in R such as [SPEI](https://github.com/sbegueria/SPEI) or don't have the Standardized Groundwater Index such as [climate_indices](https://github.com/monocongo/climate_indices). This package uses popular Python packages such as Pandas and Scipy to make it easy but versitile for the user to calculate the drought indices. 

Due to the flexibility of this package all [distributions](https://docs.scipy.org/doc/scipy/reference/stats.html) available in the SciPy library can be used to fit the data. However, there are recommendations for the SPEI, SPI an SGI.

Note that this package does not calculate potential evaporation, we refer to [pyet](https://github.com/phydrus/pyet) for that. All time series have to be calculated in advance and be provided as a pandas Series. 
