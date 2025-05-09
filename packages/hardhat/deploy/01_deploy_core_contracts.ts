import { HardhatRuntimeEnvironment } from "hardhat/types";
import { DeployFunction } from "hardhat-deploy/types";

const deployChainPilot: DeployFunction = async function (hre: HardhatRuntimeEnvironment) {
  const { deployer } = await hre.getNamedAccounts();
  const { deploy, get } = hre.deployments;

  // --- Deploying Executor ---
  const executor = await deploy("ChainPilotExecutor", {
    from: deployer,
    args: [],
    log: true,
    autoMine: true,
    waitConfirmations: 1,
  });

  console.log(`Executor deployed at: ${executor.address}`);
  console.log("========////////////////////////////////////////////////////////////====");

  // --- Deploying Scheduler ---
  const scheduler = await deploy("ChainPilotScheduler", {
    from: deployer,
    args: [executor.address],
    log: true,
    autoMine: true,
    waitConfirmations: 1,
  });

  console.log(`Scheduler deployed at: ${scheduler.address}`);
  console.log("========////////////////////////////////////////////////////////////====\n");

  console.log(`Executor address set to: ${executor.address}`);

  // --- Verification ---
  if (process.env.VERIFY_CONTRACTS === "true") {
    console.log("⏳Verifying contracts...");
    await hre.run("verify:verify", {
      address: executor.address,
      constructorArguments: [],
    });

    await hre.run("verify:verify", {
      address: scheduler.address,
      constructorArguments: [executor.address],
    });
    console.log("Verification complete");
  }
};

export default deployChainPilot;
deployChainPilot.tags = ["ChainPilot", "ChainPilotExecutor", "ChainPilotScheduler"];
