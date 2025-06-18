import re
from astropy import units as u, constants as c
import numpy as np
from typing import List, Tuple, Optional, Dict, Union
import pint.models
import pint.toa
from loguru import logger as log

# these can be set elsewhere or overridden if needed
# format is:
# top-level block:
#   can be specified by ``all`` (applies to all entries)
#   or name of parameter (and then only applies if that parameter is present)
# within each block can specify:
#   ``required``: list, all parameters must be present and fittable
#   ``optional``: list, parameters may be present, but if they are must be fittable
#   ``optional_sets``: list of lists, if any parameter in the list is present then all must be (and must be fittable)
binary_params = {
    "ELL1": {
        "all": {
            "required": ["A1", "TASC", "EPS1", "EPS2"],
            "optional": ["A1DOT"],
            "optional_sets": [["EPS1DOT", "EPS2DOT"]],
        },
        "PB": {"required": ["PBDOT"], "optional_sets": [["M2", "SINI"]]},
    },
    "ELL1H": {
        "all": {
            "required": ["A1", "TASC", "EPS1", "EPS2", "A1DOT", "H3", "PBDOT"],
            "optional_sets": [["EPS1DOT", "EPS2DOT"]],
        }
    },
    "DD": {
        "all": {
            "required": ["A1" "E", "T0", "PB", "OM"],
            "optional": ["PBDOT", "A1DOT", "OMDOT", "EDOT"],
            "optional_sets": [["EPS1DOT", "EPS2DOT"]],
        }
    },
    "DDK": {
        "all": {
            "required": ["A1", "E", "T0", "PB", "OM", "M2", "K96", "KOM", "KIN"],
            "optional": ["PBDOT", "A1DOT", "OMDOT", "EDOT"],
        }
    },
}


class DataChecker:
    def __init__(self, model: pint.models.TimingModel, toas: pint.toa.TOAs):
        """
        Check data sets (timing model and TOAs) for problems.

        Abstract class that should be sub-classed for specific cases.
        """
        self.m = model
        self.t = toas

    def check(self):
        raise NotImplementedError("This class should not be used directly")

    def raise_or_warn(self, message: str, exception: Union[None, bool, type]):
        """Raise an exception or just warn

        Parameters
        ----------
        message : str
        exception : None or bool or Exception type

        Raises
        ------
        exception
            If it is not None or False
        """
        if not (exception is None or (isinstance(exception, bool) and not exception)):
            raise exception(message)
        log.warning(message)

    def check_parameter(
        self,
        p: str,
        raiseexcept: Optional[bool] = True,
        require_unfrozen: Optional[bool] = True,
    ) -> bool:
        """
        Check for the existence of a single parameter, optionally it must be unfrozen

        Parameters
        ----------
        p : str
            Parameter name
        raiseexcept: bool, optional
            Will an error raise an exception (default) or just a warning
        require_unfrozen: bool, optional
            Should it also be unfrozen?

        Returns
        -------
        bool
            True if the checks pass, False otherwise

        Raises
        ------
        KeyError
            If the check fails and ``raiseexcept`` is True
        """
        if not (p in self.m.params and self.m[p].value is not None):
            self.raise_or_warn(
                f"Parameter '{p}' not found in timing model",
                KeyError if raiseexcept else None,
            )
            return False
        if require_unfrozen:
            if self.m[p].frozen:
                self.raise_or_warn(
                    f"Parameter '{p}' found in timing model but frozen",
                    KeyError if raiseexcept else None,
                )
                return False
        return True

    def check_optional_parameter(
        self,
        p: str,
        raiseexcept: Optional[bool] = True,
        require_unfrozen: Optional[bool] = True,
    ) -> bool:
        """
        Check for the existence of a single optional parameter.
        If it does not exist or has no value then nothing is done.
        Optionally it must be unfrozen

        Parameters
        ----------
        p : str
            Parameter name
        raiseexcept: bool, optional
            Will an error raise an exception (default) or just a warning
        require_unfrozen: bool, optional
            Should it also be unfrozen?

        Returns
        -------
        bool
            True if the checks pass, False otherwise

        Raises
        ------
        KeyError
            If the check fails and ``raiseexcept`` is True
        """
        if p not in self.m.params or self.m[p].value is None:
            return True
        if require_unfrozen:
            if self.m[p].frozen:
                self.raise_or_warn(
                    f"Parameter '{p}' found in timing model but frozen",
                    KeyError if raiseexcept else None,
                )
                return False
        return True

    def check_parameter_set(
        self,
        p: List[str],
        raiseexcept: Optional[bool] = True,
        require_unfrozen: Optional[bool] = True,
    ) -> bool:
        """
        Check for the existence of a set of parameter, optionally they must be unfrozen

        Parameters
        ----------
        p : list of str
            Parameter names
        raiseexcept: bool, optional
            Will an error raise an exception (default) or just a warning
        require_unfrozen: bool, optional
            Should they also be unfrozen?

        Returns
        -------
        bool
            True if the checks pass, False otherwise

        Raises
        ------
        KeyError
            If the check fails and ``raiseexcept`` is True
        """
        return all(
            [
                self.check_parameter(
                    x, raiseexcept=raiseexcept, require_unfrozen=require_unfrozen
                )
                for x in p
            ]
        )

    def check_optional_parameter_sets(
        self,
        p: List[str],
        raiseexcept: Optional[bool] = True,
        require_unfrozen: Optional[bool] = True,
    ) -> bool:
        """
        Check for the existence of an optional set parameter: if one is there they all must be; optionally they must be unfrozen

        Parameters
        ----------
        p : list of str
            Parameter names
        raiseexcept: bool, optional
            Will an error raise an exception (default) or just a warning
        require_unfrozen: bool, optional
            Should they also be unfrozen?

        Returns
        -------
        bool
            True if the checks pass, False otherwise

        Raises
        ------
        KeyError
            If the check fails and ``raiseexcept`` is True
        """
        if any([x in self.m.params for x in p]) and not all(
            [x in self.m.params for x in p]
        ):
            self.raise_or_warn(
                f"All parameters '{p}' not found in timing model",
                KeyError if raiseexcept else None,
            )
            return False
        if all([self.m[x].value is None for x in p]):
            # parameters are there, but all are unset
            return True
        if any([self.m[x].value is None for x in p]):
            self.raise_or_warn(
                f"All parameters '{p}' found in timing model but some unset",
                KeyError if raiseexcept else None,
            )
            return False
        if require_unfrozen:
            if any([self.m[x].frozen for x in p]):
                self.raise_or_warn(
                    f"All parameters '{p}' found in timing model but some frozen",
                    KeyError if raiseexcept else None,
                )
            return False
        return True


class NameChecker(DataChecker):
    def check(
        self,
        raiseexcept: Optional[bool] = True,
    ) -> bool:
        """
        Parameters
        ----------
        raiseexcept: bool, optional
            Will an error raise an exception (default) or just a warning

        Returns
        -------
        bool
            True if the checks pass, False otherwise

        Raises
        ------
        KeyError
            If the check fails and ``raiseexcept`` is True
        """
        value = re.match(r"J\d{4}[+-]\d{4}", self.m.PSR.value) or re.match(
            r"B\d{4}[+-]\d{2}", self.m.PSR.value
        )
        if not value:
            self.raise_or_warn(
                f"Pulsar name '{self.m.PSR.value}' does not match required format",
                KeyError if raiseexcept else None,
            )
        return value


class BinaryChecker(DataChecker):
    """
    Checker for a binary system.  Identifies appropriate subclass for each binary model and runs it.

    """

    def __init__(self, model: pint.models.TimingModel, toas: pint.toa.TOAs):
        super().__init__(model, toas)
        if self.m.is_binary:
            if not self.m["BINARY"].value in binary_params.keys():
                raise KeyError(
                    f"Binary parameters not found: {self.m['BINARY'].value} not supported"
                )
            self.binary_params = binary_params[self.m["BINARY"].value]

    def check(self, raiseexcept: Optional[bool] = True) -> bool:
        """
        Parameters
        ----------
        raiseexcept: bool, optional
            Will an error raise an exception (default) or just a warning

        Returns
        -------
        bool
            True if the checks pass, False otherwise

        Raises
        ------
        KeyError
            If the check fails and ``raiseexcept`` is True
        """

        if not self.m.is_binary:
            return True

        for k in self.binary_params:
            if k != "all" and (k not in self.m.params or self.m[k] is None):
                continue
            value = self.check_parameter_set(
                self.binary_params[k]["required"],
                require_unfrozen=True,
                raiseexcept=raiseexcept,
            )
            if "optional" in self.binary_params[k]:
                for p in self.binary_params[k]["optional"]:
                    value = value and self.check_optional_parameter(
                        p, require_unfrozen=True, raiseexcept=raiseexcept
                    )
            if "optional_sets" in self.binary_params[k]:
                for p in self.binary_params[k]["optional_sets"]:
                    value = value and self.check_optional_parameter_sets(
                        p, require_unfrozen=True, raiseexcept=raiseexcept
                    )
        return value


class ParChecker(DataChecker):
    """
    Check data sets (timing model and TOAs) for certain timing parameters

    """

    def check(
        self,
        required: List[str] = ["F0", "F1", "PX", "ELONG", "ELAT", "PMELONG", "PMELAT"],
        excluded: List[str] = ["F2"],
        required_value: Dict = {
            "PLANET_SHAPIRO": True,
            "EPHEM": "DE440",
            "CLOCK": "TT(BIPM2023)",
            "CORRECT_TROPOSPHERE": True,
        },
        othercheckers=[NameChecker, BinaryChecker],
        raiseexcept: Optional[bool] = True,
    ) -> bool:
        """
        Check the data

        Parameters
        ----------
        required: list
            parameter names that must be present
        excluded: list
            parameter names that cannot be present
        required_value : dict
            parameter names and values that must be present
        raiseexcept: bool, optional
            Will an error raise an exception (default) or just a warning

        Returns
        -------
        bool
            True if the checks pass, False otherwise

        Raises
        ------
        KeyError
            If the check fails and ``raiseexcept`` is True
        """
        value = self.check_parameter_set(
            required, raiseexcept=raiseexcept, require_unfrozen=True
        )
        if not value:
            return value
        value = self.check_parameter_set(
            required_value.keys(), raiseexcept=raiseexcept, require_unfrozen=False
        )
        if not value:
            return value
        for p in excluded:
            if p in self.m.params and self.m[p].value is not None:
                self.raise_or_warn(
                    f"Excluded parameter '{p}' is  present in timing model",
                    KeyError if raiseexcept else None,
                )
                return False
        for p in required_value.keys():
            if not (self.m[p].value == required_value[p]):
                self.raise_or_warn(
                    f"Required parameter '{p}' is present, but value is '{self.m[p].value}, not {required_value[p]}",
                    KeyError if raiseexcept else None,
                )
                return False
        for checkername in othercheckers:
            checker = checkername(self.m, self.t)
            value = checker.check(raiseexcept=raiseexcept)
            if not value:
                return False
        return True


class TOAChecker(DataChecker):
    """Check that the TOAs all have the correct version

    Check that no TOAs exist in a specified range with a specified backend
    """

    def check(
        self,
        version="2025.02.05-1fb9ef4.01.31-08c1687",
        badranges={"PUPPI": [57984, 58447]},
        raiseexcept: Optional[bool] = True,
    ) -> bool:
        """
        Check the data

        Parameters
        ----------
        version: str
            TOA version string
        badranges : dict
            Dictionary of backend and MJD ranges that must be excluded
        raiseexcept: bool, optional
            Will an error raise an exception (default) or just a warning

        Returns
        -------
        bool
            True if the checks pass, False otherwise

        Raises
        ------
        ValueError
            If the check fails and ``raiseexcept`` is True
        """
        value = np.all(self.t["ver"] == version)
        if not value:
            self.raise_or_warn(
                f"TOA version is not '{version}' for all TOAs",
                ValueError if raiseexcept else None,
            )
            return False
        for k in badranges.keys():
            mjds = self.t.get_mjds()[self.t["be"] == k].value
            filtered_mjds = (mjds >= badranges[k][0]) and (mjds <= badranges[k][1])
            value = np.any(filtered_mjds)
            if value:
                self.raise_or_warn(
                    f"TOAs for backend '{k}' contain {filtered_mjds.sum()} values between MJD {badranges[k][0]} and {badranges[k][1]}",
                    ValueError if raiseexcept else None,
                )
            return False
        return True


class JumpChecker(DataChecker):
    """
    Check data sets (timing model and TOAs) for timing jumps.

    All TOAs should be covered by JUMPs or -to flags except for a set defined by a single list of flags
    """

    def check(
        self,
        keys: Optional[List[Tuple]] = [("f"), ("fe", "be")],
        raiseexcept: Optional[bool] = True,
    ) -> bool:
        """
        Check the data

        Parameters
        ----------
        keys: list of tuples, optional
            Each element of the list is a set of one or more TOA flags to check for establishing a single dataset
        raiseexcept: bool, optional
            Will an error raise an exception (default) or just a warning

        Returns
        -------
        bool
            True if the checks pass, False otherwise

        Raises
        ------
        KeyError
            If the check fails and ``raiseexcept`` is True
        """
        jump_or_offset = np.zeros(len(self.t), dtype=bool)
        offsets, offset_indices = self.t.get_flag_value("to", np.nan, float)
        if len(offset_indices) > 0:
            jump_or_offset[np.array(offset_indices)] = True
        jump_indices = {}
        for p in self.m.components["PhaseJump"].params:
            jump_indices[p] = self.m[p].select_toa_mask(self.t)
            if (len(jump_indices[p]) == 0) and (not self.m[p].frozen):
                v = " ".join(self.m[p].key_value)
                self.raise_or_warn(
                    f"Jump '{p}' = '{self.m[p].key} {v}' has 0 TOAs but is not frozen",
                    KeyError if raiseexcept else None,
                )
            jump_or_offset[jump_indices[p]] = True
        not_jumped_or_offset = np.setdiff1d(
            np.arange(len(self.t)), np.where(jump_or_offset)[0]
        )
        if len(not_jumped_or_offset) == 0:
            self.raise_or_warn(
                f"All {len(self.t)} TOAs are covered by a JUMP or -to flag",
                KeyError if raiseexcept else None,
            )
            return False
        keyset = []
        passes = False
        for k in keys:
            keyset.append(np.array(self.t[k][not_jumped_or_offset]))
            if len(np.unique(keyset[-1])) == 1:
                log.info(
                    f"{len(not_jumped_or_offset)} TOAs are not covered by JUMPs or -to flags, but have the same value of '{k}' = '{list(np.unique(keyset[-1]))}'"
                )
                passes = True
                break
        if not passes:
            self.raise_or_warn(
                f"{len(not_jumped_or_offset)} TOAs are not covered by JUMPs or -to flags and do not have common sets of flags",
                KeyError if raiseexcept else None,
            )
            return False

        if self.t.is_wideband():
            jump_or_offset = np.zeros(len(self.t), dtype=bool)
            jump_indices = {}
            for p in self.m.components["DispersionJump"].params:
                jump_indices[p] = self.m[p].select_toa_mask(t)
                if (len(jump_indices[p]) == 0) and (not self.m[p].frozen):
                    v = " ".join(self.m[p].key_value)
                    self.raise_or_warn(
                        f"DMJump '{p}' = '{self.m[p].key} {v}' has 0 TOAs but is not frozen",
                        KeyError if raiseexcept else None,
                    )
                jump_or_offset[jump_indices[p]] = True
            not_jumped_or_offset = np.setdiff1d(
                np.arange(len(self.t)), np.where(jump_or_offset)[0]
            )
            if len(not_jumped_or_offset) == 0:
                self.raise_or_warn(
                    f"All {len(self.t)} TOAs are covered by a DMJUMP",
                    KeyError if raiseexcept else None,
                )
                return False
            keyset = []
            passes = False
            for k in keys:
                keyset.append(np.array(self.t[k][not_jumped_or_offset]))
                if len(np.unique(keyset[-1])) == 1:
                    log.info(
                        f"{len(not_jumped_or_offset)} TOAs are not covered by DMJUMPs, but have the same value of '{k}' = '{list(np.unique(keyset[-1]))}'"
                    )
                    passes = True
                    break
            if not passes:
                self.raise_or_warn(
                    f"{len(not_jumped_or_offset)} TOAs are not covered by DMJUMPs and do not have common sets of flags",
                    KeyError if raiseexcept else None,
                )
                return False

        return True
