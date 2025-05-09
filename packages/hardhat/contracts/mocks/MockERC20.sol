// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {IERC20} from "@openzeppelin/contracts/token/ERC20/IERC20.sol";  

abstract contract MockERC20 is IERC20 {
    string public name = "MockERC20";
    string public symbol = "MOCK";
    uint8 public decimals = 18;


}