const { expect } = require("chai");
const { ethers } = require("hardhat");
const { loadFixture, time } = require("@nomicfoundation/hardhat-network-helpers");

const State = {
  None: 0n,
  Funded: 1n,
  Delivered: 2n,
  Disputed: 3n,
  Released: 4n,
  Refunded: 5n,
  Resolved: 6n,
};

const HOUR = 60 * 60;
const DAY = 24 * HOUR;
const VALUE = ethers.parseEther("1");
const TERMS = ethers.id("synthetic trade terms v1");
const DELIVERY = ethers.id("synthetic delivery evidence v1");

describe("SafeTradeEscrow", function () {
  async function deployFixture() {
    const [admin, buyer, seller, arbiter, other, pauser, secondArbiter] =
      await ethers.getSigners();
    const Factory = await ethers.getContractFactory("SafeTradeEscrow");
    const escrow = await Factory.deploy(admin.address);
    await escrow.waitForDeployment();
    const arbiterRole = await escrow.ARBITER_ROLE();
    const pauserRole = await escrow.PAUSER_ROLE();
    await escrow.connect(admin).grantRole(arbiterRole, arbiter.address);

    async function create(overrides = {}) {
      const now = await time.latest();
      const args = {
        buyer,
        seller: seller.address,
        arbiter: arbiter.address,
        deadline: now + 2 * HOUR,
        termsHash: TERMS,
        value: VALUE,
        ...overrides,
      };
      const id = await escrow.nextEscrowId();
      const tx = await escrow
        .connect(args.buyer)
        .createEscrow(
          args.seller,
          args.arbiter,
          args.deadline,
          args.termsHash,
          { value: args.value }
        );
      await tx.wait();
      return id;
    }

    async function createDelivered(overrides = {}) {
      const id = await create(overrides);
      await escrow.connect(seller).markDelivered(id, DELIVERY);
      return id;
    }

    async function createDisputed(overrides = {}) {
      const id = await createDelivered(overrides);
      await escrow.connect(buyer).raiseDispute(id);
      return id;
    }

    return {
      escrow,
      admin,
      buyer,
      seller,
      arbiter,
      other,
      pauser,
      secondArbiter,
      arbiterRole,
      pauserRole,
      create,
      createDelivered,
      createDisputed,
    };
  }

  describe("deployment and roles", function () {
    it("sets the administrator, pauser, constants, and first ID", async function () {
      const { escrow, admin, pauserRole } = await loadFixture(deployFixture);
      expect(await escrow.hasRole(await escrow.DEFAULT_ADMIN_ROLE(), admin)).to.equal(true);
      expect(await escrow.hasRole(pauserRole, admin)).to.equal(true);
      expect(await escrow.nextEscrowId()).to.equal(1);
      expect(await escrow.ARBITER_FEE_BPS()).to.equal(100);
      expect(await escrow.REVIEW_PERIOD()).to.equal(3 * DAY);
    });

    it("rejects a zero administrator", async function () {
      const Factory = await ethers.getContractFactory("SafeTradeEscrow");
      await expect(Factory.deploy(ethers.ZeroAddress)).to.be.revertedWithCustomError(
        Factory,
        "InvalidAddress"
      );
    });

    it("lets the administrator grant and revoke arbiter eligibility", async function () {
      const { escrow, admin, other, arbiterRole } = await loadFixture(deployFixture);
      await escrow.connect(admin).grantRole(arbiterRole, other);
      expect(await escrow.hasRole(arbiterRole, other)).to.equal(true);
      await escrow.connect(admin).revokeRole(arbiterRole, other);
      expect(await escrow.hasRole(arbiterRole, other)).to.equal(false);
    });

    it("rejects role management by a non-administrator", async function () {
      const { escrow, buyer, other, arbiterRole } = await loadFixture(deployFixture);
      await expect(
        escrow.connect(buyer).grantRole(arbiterRole, other)
      ).to.be.revertedWithCustomError(escrow, "AccessControlUnauthorizedAccount");
    });

    it("rejects pause by an account without the pauser role", async function () {
      const { escrow, buyer } = await loadFixture(deployFixture);
      await expect(escrow.connect(buyer).pause()).to.be.revertedWithCustomError(
        escrow,
        "AccessControlUnauthorizedAccount"
      );
    });
  });

  describe("creation and validation", function () {
    it("creates a funded escrow and emits complete creation data", async function () {
      const { escrow, buyer, seller, arbiter } = await loadFixture(deployFixture);
      const now = await time.latest();
      const deadline = now + 2 * HOUR;
      await expect(
        escrow
          .connect(buyer)
          .createEscrow(seller, arbiter, deadline, TERMS, { value: VALUE })
      )
        .to.emit(escrow, "EscrowCreated")
        .withArgs(1, buyer, seller, arbiter, VALUE, deadline, TERMS);

      const item = await escrow.getEscrow(1);
      expect(item.buyer).to.equal(buyer);
      expect(item.seller).to.equal(seller);
      expect(item.arbiter).to.equal(arbiter);
      expect(item.amount).to.equal(VALUE);
      expect(item.state).to.equal(State.Funded);
      expect(await escrow.totalLocked()).to.equal(VALUE);
      expect(await ethers.provider.getBalance(escrow)).to.equal(VALUE);
    });

    it("increments IDs across multiple escrows", async function () {
      const { escrow, create } = await loadFixture(deployFixture);
      expect(await create()).to.equal(1);
      expect(await create()).to.equal(2);
      expect(await escrow.nextEscrowId()).to.equal(3);
    });

    it("accepts the minimum delivery window", async function () {
      const { escrow, buyer, seller, arbiter } = await loadFixture(deployFixture);
      const deadline = (await time.latest()) + HOUR + 1;
      await expect(
        escrow
          .connect(buyer)
          .createEscrow(seller, arbiter, deadline, TERMS, { value: 1 })
      ).not.to.be.reverted;
    });

    it("accepts the maximum delivery window", async function () {
      const { escrow, buyer, seller, arbiter } = await loadFixture(deployFixture);
      const deadline = (await time.latest()) + 90 * DAY + 1;
      await expect(
        escrow
          .connect(buyer)
          .createEscrow(seller, arbiter, deadline, TERMS, { value: 1 })
      ).not.to.be.reverted;
    });

    it("rejects zero funding", async function () {
      const { escrow, buyer, seller, arbiter } = await loadFixture(deployFixture);
      await expect(
        escrow
          .connect(buyer)
          .createEscrow(seller, arbiter, (await time.latest()) + 2 * HOUR, TERMS)
      ).to.be.revertedWithCustomError(escrow, "ZeroAmount");
    });

    for (const [label, sellerSelector, arbiterSelector] of [
      ["zero seller", () => ethers.ZeroAddress, ({ arbiter }) => arbiter.address],
      ["zero arbiter", ({ seller }) => seller.address, () => ethers.ZeroAddress],
      ["buyer as seller", ({ buyer }) => buyer.address, ({ arbiter }) => arbiter.address],
      ["buyer as arbiter", ({ seller }) => seller.address, ({ buyer }) => buyer.address],
      ["same seller and arbiter", ({ seller }) => seller.address, ({ seller }) => seller.address],
    ]) {
      it(`rejects ${label}`, async function () {
        const fixture = await loadFixture(deployFixture);
        const { escrow, buyer } = fixture;
        await expect(
          escrow
            .connect(buyer)
            .createEscrow(
              sellerSelector(fixture),
              arbiterSelector(fixture),
              (await time.latest()) + 2 * HOUR,
              TERMS,
              { value: 1 }
            )
        ).to.be.revertedWithCustomError(escrow, "InvalidAddress");
      });
    }

    it("rejects an empty terms hash", async function () {
      const { escrow, buyer, seller, arbiter } = await loadFixture(deployFixture);
      await expect(
        escrow
          .connect(buyer)
          .createEscrow(
            seller,
            arbiter,
            (await time.latest()) + 2 * HOUR,
            ethers.ZeroHash,
            { value: 1 }
          )
      ).to.be.revertedWithCustomError(escrow, "InvalidHash");
    });

    it("rejects an ineligible arbiter", async function () {
      const { escrow, buyer, seller, other } = await loadFixture(deployFixture);
      await expect(
        escrow
          .connect(buyer)
          .createEscrow(
            seller,
            other,
            (await time.latest()) + 2 * HOUR,
            TERMS,
            { value: 1 }
          )
      ).to.be.revertedWithCustomError(escrow, "NotAuthorized");
    });

    it("rejects a delivery window shorter than one hour", async function () {
      const { escrow, buyer, seller, arbiter } = await loadFixture(deployFixture);
      await expect(
        escrow
          .connect(buyer)
          .createEscrow(
            seller,
            arbiter,
            (await time.latest()) + HOUR,
            TERMS,
            { value: 1 }
          )
      ).to.be.revertedWithCustomError(escrow, "DeliveryWindowTooShort");
    });

    it("rejects a past deadline", async function () {
      const { escrow, buyer, seller, arbiter } = await loadFixture(deployFixture);
      await expect(
        escrow
          .connect(buyer)
          .createEscrow(seller, arbiter, (await time.latest()) - 1, TERMS, { value: 1 })
      ).to.be.revertedWithCustomError(escrow, "DeliveryWindowTooShort");
    });

    it("rejects a delivery window longer than 90 days", async function () {
      const { escrow, buyer, seller, arbiter } = await loadFixture(deployFixture);
      await expect(
        escrow
          .connect(buyer)
          .createEscrow(
            seller,
            arbiter,
            (await time.latest()) + 90 * DAY + 2,
            TERMS,
            { value: 1 }
          )
      ).to.be.revertedWithCustomError(escrow, "DeliveryWindowTooLong");
    });

    it("rejects unknown escrow IDs", async function () {
      const { escrow } = await loadFixture(deployFixture);
      await expect(escrow.getEscrow(999)).to.be.revertedWithCustomError(
        escrow,
        "EscrowNotFound"
      ).withArgs(999);
    });
  });

  describe("delivery and deadline transitions", function () {
    it("records delivery evidence and starts a three-day review", async function () {
      const { escrow, seller, create } = await loadFixture(deployFixture);
      const id = await create();
      const before = await time.latest();
      await expect(escrow.connect(seller).markDelivered(id, DELIVERY))
        .to.emit(escrow, "DeliveryMarked");
      const item = await escrow.getEscrow(id);
      expect(item.state).to.equal(State.Delivered);
      expect(item.deliveryHash).to.equal(DELIVERY);
      expect(item.reviewDeadline).to.equal(before + 1 + 3 * DAY);
    });

    it("rejects delivery by a non-seller", async function () {
      const { escrow, buyer, create } = await loadFixture(deployFixture);
      const id = await create();
      await expect(
        escrow.connect(buyer).markDelivered(id, DELIVERY)
      ).to.be.revertedWithCustomError(escrow, "NotAuthorized");
    });

    it("rejects an empty delivery hash", async function () {
      const { escrow, seller, create } = await loadFixture(deployFixture);
      const id = await create();
      await expect(
        escrow.connect(seller).markDelivered(id, ethers.ZeroHash)
      ).to.be.revertedWithCustomError(escrow, "InvalidHash");
    });

    it("rejects duplicate delivery marking", async function () {
      const { escrow, seller, createDelivered } = await loadFixture(deployFixture);
      const id = await createDelivered();
      await expect(
        escrow.connect(seller).markDelivered(id, DELIVERY)
      ).to.be.revertedWithCustomError(escrow, "InvalidState");
    });

    it("allows delivery immediately before its deadline", async function () {
      const { escrow, seller, create } = await loadFixture(deployFixture);
      const id = await create();
      const item = await escrow.getEscrow(id);
      await time.setNextBlockTimestamp(Number(item.deliveryDeadline) - 1);
      await expect(escrow.connect(seller).markDelivered(id, DELIVERY)).not.to.be.reverted;
    });

    it("rejects delivery exactly at its deadline", async function () {
      const { escrow, seller, create } = await loadFixture(deployFixture);
      const id = await create();
      const item = await escrow.getEscrow(id);
      await time.setNextBlockTimestamp(item.deliveryDeadline);
      await expect(
        escrow.connect(seller).markDelivered(id, DELIVERY)
      ).to.be.revertedWithCustomError(escrow, "DeliveryDeadlinePassed");
    });

    it("rejects buyer timeout immediately before delivery deadline", async function () {
      const { escrow, buyer, create } = await loadFixture(deployFixture);
      const id = await create();
      const item = await escrow.getEscrow(id);
      await time.setNextBlockTimestamp(Number(item.deliveryDeadline) - 1);
      await expect(
        escrow.connect(buyer).claimRefundAfterDeadline(id)
      ).to.be.revertedWithCustomError(escrow, "DeliveryDeadlineNotReached");
    });

    it("refunds the buyer exactly at the delivery deadline", async function () {
      const { escrow, buyer, create } = await loadFixture(deployFixture);
      const id = await create();
      const item = await escrow.getEscrow(id);
      await time.setNextBlockTimestamp(item.deliveryDeadline);
      await expect(escrow.connect(buyer).claimRefundAfterDeadline(id))
        .to.emit(escrow, "EscrowRefunded")
        .withArgs(id, VALUE);
      expect((await escrow.getEscrow(id)).state).to.equal(State.Refunded);
      expect(await escrow.pendingWithdrawals(buyer)).to.equal(VALUE);
    });
  });

  describe("normal settlement and refunds", function () {
    it("lets the buyer confirm delivery and credits the seller", async function () {
      const { escrow, buyer, seller, createDelivered } = await loadFixture(deployFixture);
      const id = await createDelivered();
      await expect(escrow.connect(buyer).confirmReceipt(id))
        .to.emit(escrow, "PaymentReleased")
        .withArgs(id, VALUE);
      expect((await escrow.getEscrow(id)).state).to.equal(State.Released);
      expect(await escrow.pendingWithdrawals(seller)).to.equal(VALUE);
      expect(await escrow.totalLocked()).to.equal(0);
      expect(await escrow.totalPending()).to.equal(VALUE);
    });

    it("rejects receipt confirmation by a non-buyer", async function () {
      const { escrow, seller, createDelivered } = await loadFixture(deployFixture);
      const id = await createDelivered();
      await expect(
        escrow.connect(seller).confirmReceipt(id)
      ).to.be.revertedWithCustomError(escrow, "NotAuthorized");
    });

    it("rejects confirmation from Funded and after final settlement", async function () {
      const { escrow, buyer, create, createDelivered } = await loadFixture(deployFixture);
      const fundedId = await create();
      await expect(
        escrow.connect(buyer).confirmReceipt(fundedId)
      ).to.be.revertedWithCustomError(escrow, "InvalidState");
      const releasedId = await createDelivered();
      await escrow.connect(buyer).confirmReceipt(releasedId);
      await expect(
        escrow.connect(buyer).confirmReceipt(releasedId)
      ).to.be.revertedWithCustomError(escrow, "InvalidState");
    });

    for (const initialState of ["Funded", "Delivered", "Disputed"]) {
      it(`lets the seller refund from ${initialState}`, async function () {
        const fixture = await loadFixture(deployFixture);
        const id =
          initialState === "Funded"
            ? await fixture.create()
            : initialState === "Delivered"
              ? await fixture.createDelivered()
              : await fixture.createDisputed();
        await expect(fixture.escrow.connect(fixture.seller).refundBySeller(id))
          .to.emit(fixture.escrow, "EscrowRefunded")
          .withArgs(id, VALUE);
        expect(await fixture.escrow.pendingWithdrawals(fixture.buyer)).to.equal(VALUE);
        expect((await fixture.escrow.getEscrow(id)).state).to.equal(State.Refunded);
      });
    }

    it("rejects seller refund by another account and after settlement", async function () {
      const { escrow, buyer, seller, create } = await loadFixture(deployFixture);
      const id = await create();
      await expect(
        escrow.connect(buyer).refundBySeller(id)
      ).to.be.revertedWithCustomError(escrow, "NotAuthorized");
      await escrow.connect(seller).refundBySeller(id);
      await expect(
        escrow.connect(seller).refundBySeller(id)
      ).to.be.revertedWithCustomError(escrow, "InvalidState");
    });

    it("rejects timeout refund by a non-buyer", async function () {
      const { escrow, seller, create } = await loadFixture(deployFixture);
      const id = await create();
      await expect(
        escrow.connect(seller).claimRefundAfterDeadline(id)
      ).to.be.revertedWithCustomError(escrow, "NotAuthorized");
    });

    it("rejects timeout refund from a delivered state", async function () {
      const { escrow, buyer, createDelivered } = await loadFixture(deployFixture);
      const id = await createDelivered();
      await expect(
        escrow.connect(buyer).claimRefundAfterDeadline(id)
      ).to.be.revertedWithCustomError(escrow, "InvalidState");
    });

    it("lets the seller claim exactly at the review deadline", async function () {
      const { escrow, seller, createDelivered } = await loadFixture(deployFixture);
      const id = await createDelivered();
      const item = await escrow.getEscrow(id);
      await time.setNextBlockTimestamp(item.reviewDeadline);
      await expect(escrow.connect(seller).claimPaymentAfterReview(id))
        .to.emit(escrow, "PaymentReleased")
        .withArgs(id, VALUE);
    });

    it("rejects seller claim immediately before review deadline", async function () {
      const { escrow, seller, createDelivered } = await loadFixture(deployFixture);
      const id = await createDelivered();
      const item = await escrow.getEscrow(id);
      await time.setNextBlockTimestamp(Number(item.reviewDeadline) - 1);
      await expect(
        escrow.connect(seller).claimPaymentAfterReview(id)
      ).to.be.revertedWithCustomError(escrow, "ReviewDeadlineNotReached");
    });

    it("rejects review claim by a non-seller and in a dispute", async function () {
      const { escrow, buyer, seller, createDelivered, createDisputed } =
        await loadFixture(deployFixture);
      const deliveredId = await createDelivered();
      await expect(
        escrow.connect(buyer).claimPaymentAfterReview(deliveredId)
      ).to.be.revertedWithCustomError(escrow, "NotAuthorized");
      const disputedId = await createDisputed();
      await expect(
        escrow.connect(seller).claimPaymentAfterReview(disputedId)
      ).to.be.revertedWithCustomError(escrow, "InvalidState");
    });
  });

  describe("disputes", function () {
    it("lets the buyer dispute before review expiry", async function () {
      const { escrow, buyer, createDelivered } = await loadFixture(deployFixture);
      const id = await createDelivered();
      await expect(escrow.connect(buyer).raiseDispute(id))
        .to.emit(escrow, "DisputeRaised")
        .withArgs(id);
      expect((await escrow.getEscrow(id)).state).to.equal(State.Disputed);
    });

    it("rejects disputes by a non-buyer, from a wrong state, and at expiry", async function () {
      const { escrow, buyer, seller, create, createDelivered } =
        await loadFixture(deployFixture);
      const deliveredId = await createDelivered();
      await expect(
        escrow.connect(seller).raiseDispute(deliveredId)
      ).to.be.revertedWithCustomError(escrow, "NotAuthorized");
      const fundedId = await create();
      await expect(
        escrow.connect(buyer).raiseDispute(fundedId)
      ).to.be.revertedWithCustomError(escrow, "InvalidState");
      const expiringId = await createDelivered();
      const item = await escrow.getEscrow(expiringId);
      await time.setNextBlockTimestamp(item.reviewDeadline);
      await expect(
        escrow.connect(buyer).raiseDispute(expiringId)
      ).to.be.revertedWithCustomError(escrow, "ReviewDeadlinePassed");
    });

    it("lets the buyer withdraw a dispute by confirming receipt", async function () {
      const { escrow, buyer, seller, createDisputed } = await loadFixture(deployFixture);
      const id = await createDisputed();
      await escrow.connect(buyer).confirmReceipt(id);
      expect((await escrow.getEscrow(id)).state).to.equal(State.Released);
      expect(await escrow.pendingWithdrawals(seller)).to.equal(VALUE);
    });

    it("splits the post-fee amount and conserves all value", async function () {
      const { escrow, buyer, seller, arbiter, createDisputed } =
        await loadFixture(deployFixture);
      const id = await createDisputed();
      const fee = VALUE / 100n;
      const distributable = VALUE - fee;
      const buyerAmount = (distributable * 2500n) / 10000n;
      const sellerAmount = distributable - buyerAmount;
      await expect(escrow.connect(arbiter).resolveDispute(id, 2500))
        .to.emit(escrow, "DisputeResolved")
        .withArgs(id, buyerAmount, sellerAmount, fee);
      expect(await escrow.pendingWithdrawals(buyer)).to.equal(buyerAmount);
      expect(await escrow.pendingWithdrawals(seller)).to.equal(sellerAmount);
      expect(await escrow.pendingWithdrawals(arbiter)).to.equal(fee);
      expect(buyerAmount + sellerAmount + fee).to.equal(VALUE);
      expect(await escrow.totalPending()).to.equal(VALUE);
    });

    for (const share of [0, 10000]) {
      it(`accepts the ${share} basis-point boundary`, async function () {
        const { escrow, buyer, seller, arbiter, createDisputed } =
          await loadFixture(deployFixture);
        const id = await createDisputed();
        await escrow.connect(arbiter).resolveDispute(id, share);
        const distributable = VALUE - VALUE / 100n;
        expect(await escrow.pendingWithdrawals(buyer)).to.equal(
          share === 0 ? 0 : distributable
        );
        expect(await escrow.pendingWithdrawals(seller)).to.equal(
          share === 0 ? distributable : 0
        );
      });
    }

    it("handles a one-wei escrow without losing value to rounding", async function () {
      const { escrow, buyer, seller, arbiter, createDisputed } =
        await loadFixture(deployFixture);
      const id = await createDisputed({ value: 1n });
      await escrow.connect(arbiter).resolveDispute(id, 5000);
      expect(await escrow.pendingWithdrawals(buyer)).to.equal(0);
      expect(await escrow.pendingWithdrawals(seller)).to.equal(1);
      expect(await escrow.pendingWithdrawals(arbiter)).to.equal(0);
      expect(await escrow.totalPending()).to.equal(1);
    });

    it("rejects a share above 10,000 basis points", async function () {
      const { escrow, arbiter, createDisputed } = await loadFixture(deployFixture);
      const id = await createDisputed();
      await expect(
        escrow.connect(arbiter).resolveDispute(id, 10001)
      ).to.be.revertedWithCustomError(escrow, "InvalidShare");
    });

    it("rejects an unassigned arbiter and a non-disputed state", async function () {
      const { escrow, admin, arbiter, secondArbiter, arbiterRole, createDelivered, createDisputed } =
        await loadFixture(deployFixture);
      await escrow.connect(admin).grantRole(arbiterRole, secondArbiter);
      const disputedId = await createDisputed();
      await expect(
        escrow.connect(secondArbiter).resolveDispute(disputedId, 5000)
      ).to.be.revertedWithCustomError(escrow, "NotAuthorized");
      const deliveredId = await createDelivered();
      await expect(
        escrow.connect(arbiter).resolveDispute(deliveredId, 5000)
      ).to.be.revertedWithCustomError(escrow, "InvalidState");
    });

    it("preserves the authority of an assigned arbiter after role revocation", async function () {
      const { escrow, admin, arbiter, arbiterRole, createDisputed } =
        await loadFixture(deployFixture);
      const id = await createDisputed();
      await escrow.connect(admin).revokeRole(arbiterRole, arbiter);
      await expect(escrow.connect(arbiter).resolveDispute(id, 5000)).not.to.be.reverted;
    });
  });

  describe("withdrawal, accounting, and emergency behaviour", function () {
    it("withdraws a pending payment with checks-effects-interactions", async function () {
      const { escrow, buyer, seller, createDelivered } = await loadFixture(deployFixture);
      const id = await createDelivered();
      await escrow.connect(buyer).confirmReceipt(id);
      await expect(escrow.connect(seller).withdraw())
        .to.emit(escrow, "Withdrawal")
        .withArgs(seller, VALUE);
      expect(await escrow.pendingWithdrawals(seller)).to.equal(0);
      expect(await escrow.totalPending()).to.equal(0);
      expect(await ethers.provider.getBalance(escrow)).to.equal(0);
    });

    it("rejects withdrawal with no pending balance", async function () {
      const { escrow, buyer } = await loadFixture(deployFixture);
      await expect(escrow.connect(buyer).withdraw()).to.be.revertedWithCustomError(
        escrow,
        "NothingToWithdraw"
      );
    });

    it("restores accounting when a recipient rejects ETH", async function () {
      const { escrow, buyer, arbiter, create } = await loadFixture(deployFixture);
      const Receiver = await ethers.getContractFactory("WithdrawalReceiver");
      const receiver = await Receiver.deploy(await escrow.getAddress());
      const id = await create({ seller: await receiver.getAddress() });
      await receiver.markDelivered(id, DELIVERY);
      await escrow.connect(buyer).confirmReceipt(id);
      await receiver.configure(true, false);
      await expect(receiver.withdrawFromEscrow()).to.be.revertedWithCustomError(
        escrow,
        "TransferFailed"
      );
      expect(await escrow.pendingWithdrawals(receiver)).to.equal(VALUE);
      expect(await escrow.totalPending()).to.equal(VALUE);
    });

    it("prevents recursive withdrawal from receiving a second payment", async function () {
      const { escrow, buyer, create } = await loadFixture(deployFixture);
      const Receiver = await ethers.getContractFactory("WithdrawalReceiver");
      const receiver = await Receiver.deploy(await escrow.getAddress());
      const id = await create({ seller: await receiver.getAddress() });
      await receiver.markDelivered(id, DELIVERY);
      await escrow.connect(buyer).confirmReceipt(id);
      await receiver.configure(false, true);
      await receiver.withdrawFromEscrow();
      expect(await receiver.receiveCount()).to.equal(1);
      expect(await ethers.provider.getBalance(receiver)).to.equal(VALUE);
      expect(await escrow.pendingWithdrawals(receiver)).to.equal(0);
    });

    it("maintains balance >= locked + pending through mixed escrows", async function () {
      const { escrow, buyer, seller, create, createDelivered } =
        await loadFixture(deployFixture);
      await create();
      const releasedId = await createDelivered();
      await escrow.connect(buyer).confirmReceipt(releasedId);
      const balance = await ethers.provider.getBalance(escrow);
      expect(balance).to.be.gte(
        (await escrow.totalLocked()) + (await escrow.totalPending())
      );
      await escrow.connect(seller).withdraw();
      expect(await ethers.provider.getBalance(escrow)).to.equal(
        (await escrow.totalLocked()) + (await escrow.totalPending())
      );
    });

    it("rejects ordinary direct and fallback ETH transfers", async function () {
      const { escrow, buyer } = await loadFixture(deployFixture);
      await expect(
        buyer.sendTransaction({ to: await escrow.getAddress(), value: 1 })
      ).to.be.revertedWithCustomError(escrow, "DirectPaymentNotAllowed");
      await expect(
        buyer.sendTransaction({ to: await escrow.getAddress(), data: "0x12345678", value: 1 })
      ).to.be.revertedWithCustomError(escrow, "DirectPaymentNotAllowed");
    });

    it("treats forcibly sent ETH as unallocated excess", async function () {
      const { escrow } = await loadFixture(deployFixture);
      const ForceSender = await ethers.getContractFactory("ForceSender");
      const sender = await ForceSender.deploy({ value: 123n });
      await sender.forceSend(await escrow.getAddress());
      expect(await ethers.provider.getBalance(escrow)).to.equal(123);
      expect(await escrow.totalLocked()).to.equal(0);
      expect(await escrow.totalPending()).to.equal(0);
    });

    it("pause blocks only new admission; existing settlement and withdrawal continue", async function () {
      const { escrow, admin, buyer, seller, arbiter, createDelivered } =
        await loadFixture(deployFixture);
      const id = await createDelivered();
      await escrow.connect(admin).pause();
      await expect(
        escrow
          .connect(buyer)
          .createEscrow(
            seller,
            arbiter,
            (await time.latest()) + 2 * HOUR,
            TERMS,
            { value: 1 }
          )
      ).to.be.revertedWithCustomError(escrow, "EnforcedPause");
      await escrow.connect(buyer).confirmReceipt(id);
      await expect(escrow.connect(seller).withdraw()).not.to.be.reverted;
    });

    it("supports a delegated pauser and resumes creation after unpause", async function () {
      const { escrow, admin, buyer, seller, arbiter, pauser, pauserRole } =
        await loadFixture(deployFixture);
      await escrow.connect(admin).grantRole(pauserRole, pauser);
      await escrow.connect(pauser).pause();
      await expect(escrow.connect(pauser).unpause()).not.to.be.reverted;
      await expect(
        escrow
          .connect(buyer)
          .createEscrow(
            seller,
            arbiter,
            (await time.latest()) + 2 * HOUR,
            TERMS,
            { value: 1 }
          )
      ).not.to.be.reverted;
    });

    it("rejects unpause while active and pause while already paused", async function () {
      const { escrow, admin } = await loadFixture(deployFixture);
      await expect(escrow.connect(admin).unpause()).to.be.revertedWithCustomError(
        escrow,
        "ExpectedPause"
      );
      await escrow.connect(admin).pause();
      await expect(escrow.connect(admin).pause()).to.be.revertedWithCustomError(
        escrow,
        "EnforcedPause"
      );
    });
  });
});
