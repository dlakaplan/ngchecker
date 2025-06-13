# ngchecker

| Check | Requirement | Done by | Notes |
| ----- | ----------- | ------- | ----- | 
| Name  | Matches JXXXX+/-XXXX or BXXXX+/-XX | `NameChecker` | |
| Spin  | Only has F0, F1.  No other parameters | `ParChecker` | F0,F1 in `required`, F2 in `excluded`.  PINT will not validate if e.g., F3 is present and F2 is not |
| Astrometry | Ecliptic coordinates, including PX | `ParChecker` | PX,ELONG,ELAT,PMELONG,PMELAT in `required` |
| Binary ELL1 | Has A1, TASC, EPS1, EPS2, PBDOT, A1DOT.  | `ELL1Checker` | One subclass per binary type | 
| Binary ELL1 | One of PB, FB0 | `PINT` | PINT will not validate if both are present | 
| Binary ELL1 | M2, SINI both present and fittable or neither | `ELL1Checker` | |
| Binary ELL1 | EPS1DOT, EPS2DOT both present and fittable or neither | `ELL1Checker` | |
| Ephemeris | Matches specified version | `ParChecker` | |
| BIPM | Matches specified version | `ParChecker` | |
| Ecliptic coordinates | Model must be in ecliptic coordinates | `ParChecker` | `pint_pal` did this twice.  It also tried to convert using a function other than `PINT` supplied.  But it didn't seem to actually return the result.  Leaving out the second check/conversion |
| Troposphere | Correction included if specified | `ParChecker` | `pint_pal` inserted component if missing, but did not seem to return the result.  Leaving out the insertion |
| Planet Shapiro | Correction included if specified | `ParChecker` | `pint_pal` inserted component if missing, but did not seem to return the result.  Leaving out the insertion |
| Bad LO range | Combination of MJD and telescope excluded from TOAs | `TOAChecker` | Can specify any combination of MJDs and backend, not just one hardcoded. | 
| TOA version | Matches specified value | `TOAChecker` | |
| Jumps | All data but one *set* are covered by JUMPs or `-to` flags.  *set* can be defined by user specified flags or combinations of flags. | `JumpChecker` | |

Note that `ParChecker` can include `BinaryChecker` and `NameChecker` as sub-checks, or they can be run separately.

