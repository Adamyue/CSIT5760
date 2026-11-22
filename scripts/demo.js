const fs = require("fs");
const path = require("path");
const hre = require("hardhat");

async function recorded(txPromise) {
  const tx = await txPromise;
  const receipt = await tx.wait();
  return { hash: tx.hash, blockNumber: receipt.blockNumber };
}

async function main() {
  const signers = await hre.ethers.getSigners();
  const deployer = signers[0];
  if (!deployer) throw new Error("No deployer account configured");
  let buyer = signers[1];
  let seller = signers[2];
  let arbiter = signers[3];
  const funding = {};

  if (hre.network.name !== "hardhat") {
    const demoKeys = [
      process.env.DEMO_BUYER_PRIVATE_KEY,
      process.env.DEMO_SELLER_PRIVATE_KEY,
      process.env.DEMO_ARBITER_PRIVATE_KEY,
    ];
    if (demoKeys.some((key) => !key)) {
      throw new Error(
        "Sepolia demo requires DEMO_BUYER_PRIVATE_KEY, " +
          "DEMO_SELLER_PRIVATE_KEY, and DEMO_ARBITER_PRIVATE_KEY in ignored .env"
      );
    }
    [buyer, seller, arbiter] = demoKeys.map(
      (key) => new hre.ethers.Wallet(key, hre.ethers.provider)
    );
    const fundingAmount = hre.ethers.parseEther("0.003");
    funding.buyer = await recorded(
      deployer.sendTransaction({ to: buyer.address, value: fundingAmount })
    );
    funding.seller = await recorded(
      deployer.sendTransaction({ to: seller.address, value: fundingAmount })
    );
    funding.arbiter = await recorded(
      deployer.sendTransaction({ to: arbiter.address, value: fundingAmount })
    );
  } else if (!buyer || !seller || !arbiter) {
    throw new Error("Local demo requires four Hardhat accounts");
  }

  let contract;
  let deployment;
  const manifestPath = path.join(
    __dirname,
    "..",
    "deployments",
    `${hre.network.name}.json`
  );
  if (hre.network.name === "hardhat") {
    const Factory = await hre.ethers.getContractFactory("SafeTradeEscrow", deployer);
    contract = await Factory.deploy(deployer.address);
    await contract.waitForDeployment();
    deployment = {
      hash: contract.deploymentTransaction().hash,
      address: await contract.getAddress(),
    };
    await contract
      .connect(deployer)
      .grantRole(await contract.ARBITER_ROLE(), arbiter.address);
  } else {
    if (!fs.existsSync(manifestPath)) {
      throw new Error(`Run deploy:sepolia first; missing ${manifestPath}`);
    }
    const manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
    contract = await hre.ethers.getContractAt(
      "SafeTradeEscrow",
      manifest.address,
      deployer
    );
    deployment = {
      hash: manifest.deploymentTransactionHash,
      address: manifest.address,
    };
    if (!(await contract.hasRole(await contract.ARBITER_ROLE(), arbiter.address))) {
      await (
        await contract
          .connect(deployer)
          .grantRole(await contract.ARBITER_ROLE(), arbiter.address)
      ).wait();
    }
  }

  const latest = await hre.ethers.provider.getBlock("latest");
  const deadline = latest.timestamp + 6 * 60 * 60;
  const amount = hre.ethers.parseEther("0.001");

  const normalId = await contract.nextEscrowId();
  const normal = {
    create: await recorded(
      contract
        .connect(buyer)
        .createEscrow(
          seller.address,
          arbiter.address,
          deadline,
          hre.ethers.id("SafeTrade synthetic normal terms"),
          { value: amount }
        )
    ),
    deliver: await recorded(
      contract
        .connect(seller)
        .markDelivered(normalId, hre.ethers.id("SafeTrade synthetic normal delivery"))
    ),
    release: await recorded(contract.connect(buyer).confirmReceipt(normalId)),
  };

  const disputedId = await contract.nextEscrowId();
  const disputed = {
    create: await recorded(
      contract
        .connect(buyer)
        .createEscrow(
          seller.address,
          arbiter.address,
          deadline,
          hre.ethers.id("SafeTrade synthetic disputed terms"),
          { value: amount }
        )
    ),
    deliver: await recorded(
      contract
        .connect(seller)
        .markDelivered(
          disputedId,
          hre.ethers.id("SafeTrade synthetic disputed delivery")
        )
    ),
    dispute: await recorded(contract.connect(buyer).raiseDispute(disputedId)),
    resolve: await recorded(
      contract.connect(arbiter).resolveDispute(disputedId, 6000)
    ),
  };
  normal.sellerWithdrawal = await recorded(contract.connect(seller).withdraw());
  disputed.buyerWithdrawal = await recorded(contract.connect(buyer).withdraw());
  disputed.arbiterWithdrawal = await recorded(contract.connect(arbiter).withdraw());

  const network = await hre.ethers.provider.getNetwork();
  const evidence = {
    network: hre.network.name,
    chainId: network.chainId.toString(),
    contract: deployment.address,
    deploymentTransactionHash: deployment.hash,
    accounts: {
      deployer: deployer.address,
      buyer: buyer.address,
      seller: seller.address,
      arbiter: arbiter.address,
    },
    accountFunding: funding,
    normalFlow: { escrowId: normalId.toString(), ...normal },
    disputedFlow: { escrowId: disputedId.toString(), ...disputed },
  };

  const evidenceDirectory = path.join(__dirname, "..", "evidence");
  fs.mkdirSync(evidenceDirectory, { recursive: true });
  const outputPath = path.join(evidenceDirectory, `demo-${hre.network.name}.json`);
  fs.writeFileSync(outputPath, `${JSON.stringify(evidence, null, 2)}\n`);
  console.log(JSON.stringify(evidence, null, 2));
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
