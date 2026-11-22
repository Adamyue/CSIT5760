require("dotenv").config({ quiet: true });
require("@nomicfoundation/hardhat-chai-matchers");
require("@nomicfoundation/hardhat-ethers");
require("@nomicfoundation/hardhat-verify");
require("solidity-coverage");

const { subtask } = require("hardhat/config");
const { TASK_COMPILE_SOLIDITY_GET_SOLC_BUILD } = require("hardhat/builtin-tasks/task-names");

subtask(TASK_COMPILE_SOLIDITY_GET_SOLC_BUILD).setAction(
  async ({ solcVersion }, _hre, runSuper) => {
    if (solcVersion === "0.8.28") {
      return {
        compilerPath: require.resolve("solc/soljson.js"),
        isSolcJs: true,
        version: solcVersion,
        longVersion: "0.8.28+commit.7893614a",
      };
    }
    return runSuper();
  }
);

const configuredKeys = [
  process.env.DEPLOYER_PRIVATE_KEY,
  process.env.DEMO_BUYER_PRIVATE_KEY,
  process.env.DEMO_SELLER_PRIVATE_KEY,
  process.env.DEMO_ARBITER_PRIVATE_KEY,
].filter(Boolean);

module.exports = {
  solidity: {
    version: "0.8.28",
    settings: {
      optimizer: { enabled: true, runs: 200 },
      evmVersion: "cancun",
    },
  },
  networks: {
    sepolia: {
      url: process.env.SEPOLIA_RPC_URL || "",
      chainId: 11155111,
      accounts: configuredKeys,
    },
  },
  etherscan: { apiKey: process.env.ETHERSCAN_API_KEY || "" },
  sourcify: { enabled: false },
  mocha: { timeout: 40000 },
};
