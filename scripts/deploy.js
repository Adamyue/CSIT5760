const fs = require("fs");
const path = require("path");
const hre = require("hardhat");

async function main() {
  const [deployer, , , localArbiter] = await hre.ethers.getSigners();
  if (!deployer) throw new Error("No deployer account configured");

  const Factory = await hre.ethers.getContractFactory("SafeTradeEscrow", deployer);
  const contract = await Factory.deploy(deployer.address);
  await contract.waitForDeployment();
  const deploymentTx = contract.deploymentTransaction();
  const receipt = await deploymentTx.wait();
  const deploymentBlock = await hre.ethers.provider.getBlock(receipt.blockNumber);

  const arbiterAddress =
    process.env.ARBITER_ADDRESS ||
    (localArbiter ? localArbiter.address : undefined);
  let grantReceipt;
  if (arbiterAddress) {
    const tx = await contract.grantRole(await contract.ARBITER_ROLE(), arbiterAddress);
    grantReceipt = await tx.wait();
  }

  const network = await hre.ethers.provider.getNetwork();
  const manifest = {
    contract: "SafeTradeEscrow",
    address: await contract.getAddress(),
    network: hre.network.name,
    chainId: network.chainId.toString(),
    deployer: deployer.address,
    deploymentTransactionHash: deploymentTx.hash,
    deploymentBlockNumber: receipt.blockNumber,
    deploymentTimestamp: new Date(
      Number(deploymentBlock.timestamp) * 1000
    ).toISOString(),
    arbiter: arbiterAddress || null,
    arbiterGrantTransactionHash: grantReceipt?.hash || null,
    compiler: "0.8.28",
    optimizer: { enabled: true, runs: 200 },
    evmVersion: "cancun",
    verified: false,
    etherscanUrl:
      network.chainId === 11155111n
        ? `https://sepolia.etherscan.io/address/${await contract.getAddress()}`
        : null,
  };

  const outputDirectory = path.join(__dirname, "..", "deployments");
  fs.mkdirSync(outputDirectory, { recursive: true });
  const outputPath = path.join(outputDirectory, `${hre.network.name}.json`);
  fs.writeFileSync(outputPath, `${JSON.stringify(manifest, null, 2)}\n`);
  console.log(JSON.stringify(manifest, null, 2));

  if (hre.network.name === "sepolia" && process.env.ETHERSCAN_API_KEY) {
    console.log("Waiting for five confirmations before verification...");
    await deploymentTx.wait(5);
    await hre.run("verify:verify", {
      address: manifest.address,
      constructorArguments: [deployer.address],
    });
    manifest.verified = true;
    fs.writeFileSync(outputPath, `${JSON.stringify(manifest, null, 2)}\n`);
  } else if (hre.network.name === "sepolia") {
    console.log("Verification skipped: ETHERSCAN_API_KEY is not configured.");
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
