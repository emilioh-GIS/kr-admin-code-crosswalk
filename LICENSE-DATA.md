# Data licence and required attribution

This covers the files in `data/`. The source code in this repository is licensed
separately under MIT (see `LICENSE`).

## Where the data comes from

The codes and names in `data/` are extracted from South Korea's official SGIS
administrative-dong boundary release, obtained through the maintained redistribution
[vuski/admdongkor](https://github.com/vuski/admdongkor) (file
`ver20260701/HangJeongDong_ver20260701.geojson`). Only attribute values are extracted;
no geometry is redistributed here.

Two licences apply, and both carry forward to any derivative of these files:

1. **KOGL Type 1 (공공누리 제1유형, attribution)** — the underlying boundaries are
   released by Statistics Korea's SGIS under the Korea Open Government Licence Type 1,
   which permits free use, modification and redistribution, including commercial use,
   provided the source is attributed. This obligation persists regardless of
   modification.
   https://www.kogl.or.kr/info/licenseType1.do
2. **CC BY 4.0** — the additions and processing made by the admdongkor project
   (including its boundary corrections and code-matching index) are released under
   Creative Commons Attribution 4.0 International.
   https://creativecommons.org/licenses/by/4.0/

## Required attribution

The admdongkor project's `DATA_LICENSE` file asks that the following be preserved when
the data is used or redistributed. It is reproduced here verbatim, in both languages:

> "본 데이터는 통계청 통계지리정보서비스(SGIS, https://sgis.kostat.go.kr)에서
> 공공누리 제1유형으로 개방한 행정동 경계를 가공한 것이며(가공: vuski/admdongkor,
> https://github.com/vuski/admdongkor), CC BY 4.0으로 배포됩니다."

> "This data is derived from administrative-dong boundaries released by Statistics
> Korea SGIS (https://sgis.kostat.go.kr) under KOGL Type 1, modified by
> vuski/admdongkor (https://github.com/vuski/admdongkor), distributed under CC BY 4.0."

If you redistribute the CSVs in `data/`, or anything derived from them, keep that
attribution with them.

## No warranty

The upstream data is provided "as is" without any guarantee of accuracy or completeness,
and SGIS is not responsible for errors introduced by downstream processing. The same
applies to this repository: the files here are a convenience extraction, and where they
disagree with the source, the source is right.
