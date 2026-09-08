# Full Data Release of the Daya Bay Reactor Neutrino Experiment

[![zenodo](https://img.shields.io/badge/zenodo-data-green?logo=zenodo&logoColor=green)](https://doi.org/10.5281/zenodo.17587229)
[![github](https://img.shields.io/badge/github-data-green?logo=github)](https://github.com/dayabay-experiment/dayabay-data-official)
[![pypi](https://img.shields.io/badge/pypi-data-green?logo=pypi&logoColor=green)](https://pypi.org/project/dayabay-data-official)
[![github-code](https://img.shields.io/badge/github-code-blue?logo=github)](https://github.com/dagflow-team/dayabay-model)
[![pypi-code](https://img.shields.io/badge/pypi-code-blue?logo=pypi&logoColor=green)](https://pypi.org/project/dayabay-model)
[![CC BY 4.0](https://img.shields.io/badge/License-CC%20BY%204.0-lightgrey.svg)](https://creativecommons.org/licenses/by/4.0/)


## Summary

The repository contains the full (analysis) Daya Bay data set of inverse-beta-decay (IBD) candidates (reactor electron antineutrino interactions) with the final-state neutron captured on gadolinium. The dataset and supplementary data are sufficient to reproduce the measurement of neutrino oscillation parameters sin²2θ₁₃ and Δm²₃₂, published in [Phys.Rev.Lett. 130 (2023) 16, 161802](https://doi.org/10.1103/PhysRevLett.130.161802).

The Daya Bay Reactor Neutrino Experiment took data from 2011 to 2020 in China. It obtained a sample of 5.55 million IBD events with the final-state neutron captured on gadolinium (nGd). This sample was collected by eight identically designed antineutrino detectors (AD) observing antineutrino flux from six nuclear power plants located at baselines between 400 m and 2 km. It covers 3158 days of operation.

Code is provided elsewhere to read the dataset and produce a measurement of sin²2θ₁₃ and Δm²₃₂, consistent with the publication.

## Citation statement

If you use the dataset, cite the following sources:

[1] [Daya Bay Collaboration, “Full Data Release of the Daya Bay Reactor Neutrino Experiment”, v1.0.0. Zenodo, DOI:10.5281/zenodo.17587229; 2025](https://doi.org/10.5281/zenodo.17587229).

[2] [F. P. An et al. (Daya Bay collaboration), “Precision Measurement of Reactor Antineutrino Oscillation at Kilometer-Scale Baselines by Daya Bay”, Phys. Rev. Lett. 130,161802 (2023), DOI: 10.1103/PhysRevLett.130.161802](https://doi.org/10.1103/PhysRevLett.130.161802).

## The dataset organization

The analysis dataset contains all the necessary inputs, needed to perform a measurement of sin²2θ₁₃ and Δm²₃₂. It is available in four different formats: hdf5, npz, root and tsv (plain text, compressed).

The detailed information on the contents of the files and formats is provided in one of dedicated readme files: [hdf5](src/dayabay_data_official/hdf5/README.md), [npz](src/dayabay_data_official/npz/README.md), [root](src/dayabay_data_official/root/README.md), [tsv](src/dayabay_data_official/tsv/README.md).

## Data availability

The main storage of the data is [Zenodo](https://doi.org/10.5281/zenodo.17587229).
A few alternative storage locations are available, including:

- Full dataset and analysis dataset:
    * [Zenodo](https://zenodo.org/communities/dayabay): https://doi.org/10.5281/zenodo.17587229
    * [NHEPSDC](https://www.nhepsdc.cn/resource/particle/dayabay): https://doi.org/DOI:10.12402/opendata/DYB/20251205202440
- Analysis dataset:
    * [GitHub](https://github.com/dayabay-experiment): https://github.com/dayabay-experiment/dayabay-data-official
    * [PYPI](https://pypi.org/org/dayabay-experiment): https://pypi.org/project/dayabay-data-official

If you host a copy of the dataset, it should be supplemented with the current description.

## Feedback and contacts

It is advised to use discussions and issues of the [GitHub dataset repository](https://github.com/dayabay-experiment/dayabay-data-official) as a main channel to provide feedback or request additional details related to the dataset itself.

If a personal contact is desired, please, contact Zeyuan Yu (<yuzy@ihep.ac.cn>) and Maxim Gonchar (<gonchar@jinr.ru>).

## Analysis code

A dedicated python module [`dayabay-model`](https://github.com/dagflow-team/dayabay-model) is provided, which is able to read analysis data in any of the formats and provide predicted IBD spectra for each AD, the χ² function, or a result of any intermediate calculation. The module also contains a few minimal examples on how to work with the model and extract data from it. At this moment the latest version of `dayabay-model`, consistent with the dataset, is v0.4.2.

More comprehensive examples of the data analysis are available in [`dayabay-analysis`](https://github.com/dagflow-team/dayabay-analysis) repository. Commands to perform the oscillation fit to the full Daya Bay dataset is provided as well.

The code above depends on a few other Python modules, developed to support the analysis. The dependencies are automatically resolved via `pip` when the model is installed.

## Acknowledgements

The results published here are in whole or in part based on the data released as Open-Access by the Daya Bay Collaboration supported by
the Ministry of Science and Technology of China,
the U.S. Department of Energy,
the Chinese Academy of Sciences,
the CAS Center for Excellence in Particle Physics,
the National Natural Science Foundation of China,
the New Cornerstone Science Foundation,
the Guangdong provincial government,
the Shenzhen municipal government,
the China General Nuclear Power Group,
the Research Grants Council of the Hong Kong Special Administrative Region of China,
the National Science and Technology Council and the Ministry of Education in Taiwan,
the U.S. National Science Foundation,
the Ministry of Education, Youth, and Sports of the Czech Republic,
the Charles University Research Centre UNCE,
and the Joint Institute of Nuclear Research in Dubna, Russia.
