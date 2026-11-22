"""Fill CSIT5760_Final_Project_Report_Template.docx with SafeTrade content."""

from copy import deepcopy
from pathlib import Path

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt
from docx.text.paragraph import Paragraph


ROOT = Path(__file__).resolve().parents[1]
TEMPLATE = ROOT / "CSIT5760_Final_Project_Report_Template.docx"
OUTPUT = ROOT / "report" / "report.docx"


def set_runs(paragraph, text, bold=None):
    paragraph.clear()
    run = paragraph.add_run(text)
    if bold is not None:
        run.bold = bold
    return paragraph


def insert_after(paragraph, text, style=None):
    new_p = deepcopy(paragraph._p)
    paragraph._p.addnext(new_p)
    new_para = Paragraph(new_p, paragraph._parent)
    if style is not None:
        new_para.style = style
    set_runs(new_para, text)
    return new_para


def replace_section(paragraphs_by_heading, heading, texts):
    placeholder = paragraphs_by_heading[heading]
    if not texts:
        set_runs(placeholder, "")
        return placeholder
    set_runs(placeholder, texts[0])
    cursor = placeholder
    for text in texts[1:]:
        cursor = insert_after(cursor, text, style=placeholder.style)
    return cursor


def set_toc_field(paragraph):
    paragraph.clear()
    run = OxmlElement("w:r")
    begin = OxmlElement("w:fldChar")
    begin.set(qn("w:fldCharType"), "begin")
    instruction = OxmlElement("w:instrText")
    instruction.set(qn("xml:space"), "preserve")
    instruction.text = ' TOC \\o "1-3" \\h \\z \\u '
    separate = OxmlElement("w:fldChar")
    separate.set(qn("w:fldCharType"), "separate")
    placeholder = OxmlElement("w:t")
    placeholder.text = "Update the table of contents in Word before final PDF export."
    end = OxmlElement("w:fldChar")
    end.set(qn("w:fldCharType"), "end")
    for element in (begin, instruction, separate, placeholder, end):
        run.append(element)
    paragraph._p.append(run)


def insert_picture_after(paragraph, image_path, caption):
    picture = insert_after(paragraph, "", style=paragraph.style)
    picture.alignment = WD_ALIGN_PARAGRAPH.CENTER
    picture.add_run().add_picture(str(image_path), width=Inches(6.2))
    caption_paragraph = insert_after(picture, caption, style="Caption")
    caption_paragraph.alignment = WD_ALIGN_PARAGRAPH.CENTER
    return caption_paragraph


def insert_code_after(paragraph, label, code):
    caption = insert_after(paragraph, label, style="Caption")
    code_paragraph = insert_after(caption, code, style="Code Block")
    for run in code_paragraph.runs:
        run.font.name = "Consolas"
        run.font.size = Pt(9)
        run._element.get_or_add_rPr().rFonts.set(qn("w:ascii"), "Consolas")
        run._element.get_or_add_rPr().rFonts.set(qn("w:hAnsi"), "Consolas")
    return code_paragraph


def set_cell(cell, text):
    if not cell.paragraphs:
        cell.text = text
        return
    first = cell.paragraphs[0]
    set_runs(first, text)
    for extra in cell.paragraphs[1:]:
        set_runs(extra, "")


def fill_table(table, rows, start_row=1):
    needed = start_row + len(rows)
    while len(table.rows) < needed:
        table.add_row()
    for offset, values in enumerate(rows):
        row = table.rows[start_row + offset]
        for col, value in enumerate(values):
            set_cell(row.cells[col], value)
    for index in range(needed, len(table.rows)):
        for cell in table.rows[index].cells:
            set_cell(cell, "")


def clear_guidance_tables(document):
    for table in list(document.tables):
        joined = "\n".join(cell.text for row in table.rows for cell in row.cells)
        if joined.strip().startswith("GUIDANCE"):
            table._element.getparent().remove(table._element)


def main():
    document = Document(TEMPLATE)
    if "Code Block" not in [style.name for style in document.styles]:
        code_style = document.styles.add_style(
            "Code Block", WD_STYLE_TYPE.PARAGRAPH
        )
        code_style.base_style = document.styles["Body Text"]
        code_style.font.name = "Consolas"
        code_style.font.size = Pt(9)
        code_style.element.rPr.rFonts.set(qn("w:ascii"), "Consolas")
        code_style.element.rPr.rFonts.set(qn("w:hAnsi"), "Consolas")

    for section in document.sections:
        for text_node in section.header._element.iter(qn("w:t")):
            if text_node.text:
                text_node.text = text_node.text.replace(
                    "Final Project Report Template",
                    "SafeTrade Final Project Report",
                )

    for paragraph in document.paragraphs:
        text = paragraph.text.strip()
        if text == "Individual Project Template":
            set_runs(paragraph, "SafeTrade Escrow Project")
        elif text.startswith("Replace all bracketed"):
            set_runs(paragraph, "")
        elif text == "Right-click and select Update Field":
            set_toc_field(paragraph)
        elif text.startswith("Update the table in Word"):
            set_runs(paragraph, "")

    cover = document.tables[0]
    fill_table(
        cover,
        [
            ["Project title", "SafeTrade: Smart-Contract Escrow with Delivery and Review Deadlines"],
            ["Student name", "YUE Pu"],
            ["Student ID", "20944719"],
            ["Programme / course", "CSIT5760 Blockchain and Smart Contracts"],
            ["Instructor", "Course instructor"],
            ["Submission date", "22 November 2026"],
            ["Repository / package", "20944719_YUE_Pu_CSIT5760_FinalProject.zip"],
        ],
        start_row=0,
    )

    by_heading = {}
    current = None
    for paragraph in document.paragraphs:
        style = paragraph.style.name if paragraph.style else ""
        text = paragraph.text.strip()
        if style.startswith("Heading"):
            current = text
            continue
        if current and text.startswith("[Write your response here"):
            by_heading[current] = paragraph
            current = None
        elif current and text.startswith("[1] Author/Organisation"):
            by_heading[current] = paragraph
            current = None

    replace_section(
        by_heading,
        "Abstract",
        [
            "SafeTrade addresses counterparty risk in peer-to-peer trades by holding Sepolia ETH until delivery is accepted, a deadline authorizes a unilateral exit, or an assigned arbiter resolves a dispute. The Solidity 0.8.28 contract combines an explicit six-state lifecycle with OpenZeppelin AccessControl, Pausable, and ReentrancyGuard [1]. It stores hashes rather than raw trade terms or evidence and uses independent pull payments so one rejecting recipient cannot block others. Validation combined 61 automated positive, negative, boundary, state, and adversarial tests with manual review and Slither 0.11.6 analysis [4]. The production contract achieved 100% statement, function, and line coverage and 98.72% branch coverage. Slither reported no High or Medium findings; its five Low timestamp findings and one Informational low-level-call finding were interpreted, tested, and accepted with documented controls. The final bytecode was deployed and source-verified on Ethereum Sepolia at 0xf4D4eCc3420495000bbfE6719f22b8F3D8fdcf0E [5][6]. Public normal and disputed flows completed successfully. Residual limitations include trusted-arbiter availability, public metadata and hashes, normal timestamp tolerance, and user-key compromise.",
        ],
    )
    replace_section(
        by_heading,
        "1.1 Project Title",
        ["SafeTrade: Smart-Contract Escrow with Delivery and Review Deadlines"],
    )
    replace_section(
        by_heading,
        "1.2 Objectives",
        [
            "O1 Implement a Solidity 0.8.x escrow with six operational states plus a None sentinel. Achieved.",
            "O2 Enforce participant permissions and OpenZeppelin AccessControl for administrator, pauser, and arbiter eligibility. Achieved.",
            "O3 Secure ETH with pull payments, checks-effects-interactions, accounting invariants, and ReentrancyGuard. Achieved.",
            "O4 Provide at least 40 automated tests with at least 95% line and 90% branch coverage. Achieved: 61 tests; 100% lines; 98.72% branches.",
            "O5 Complete Slither and manual security review, remediating or justifying High/Medium issues. Achieved: zero High/Medium detector findings.",
            "O6 Deploy to Sepolia, verify on Etherscan, and record normal and disputed settlements. Achieved with verified source and public transaction hashes.",
        ],
    )
    replace_section(
        by_heading,
        "1.3 Background and Motivation",
        [
            "Peer-to-peer trades between strangers create counterparty risk: a buyer who pays first may never receive delivery, while a seller who delivers first may never be paid. Centralised escrow reduces that risk but requires trust in an operator that custodies funds and applies rules.",
            "SafeTrade holds Sepolia ETH until publicly inspectable conditions authorize release, refund, or arbitration. The administrator manages eligibility and admission pausing but cannot withdraw or redirect escrowed funds. Blockchain is appropriate because custody and settlement rules can be enforced independently of the platform operator, and contract state, deadlines, and settlement events are independently verifiable.",
            "Trade descriptions and delivery evidence remain off-chain. Only hashes are stored. Those hashes provide tamper evidence, not confidentiality or proof that the content is true.",
        ],
    )
    replace_section(
        by_heading,
        "1.4 Scope and Limitations",
        [
            "Implemented scope: concurrent ETH escrows; delivery and review deadlines; voluntary seller refund; buyer release; buyer delivery timeout; seller review timeout; disputes; assigned-arbiter split with a 1% fee; independent withdrawals; and admission pausing.",
            "Exclusions: ERC-20/NFT custody, delivery oracles, decentralised arbitration, upgradeable proxies, mainnet deployment, and a full web front end. Interaction is demonstrated with Hardhat and Python Web3 scripts.",
            "Assumptions and limitations: the administrator vets arbiters; arbiter assignment is fixed at creation; a non-responsive arbiter can delay a disputed case while parties disagree; timestamps have validator tolerance; and on-chain hashes are public.",
        ],
    )
    architecture_end = replace_section(
        by_heading,
        "2.1 Architecture Overview",
        [
            "SafeTradeEscrow is a single non-upgradeable contract that custodies ETH, records escrow metadata, and credits pull-payment balances. Off-chain files and messages are represented only by termsHash and deliveryHash. The administrator grants ARBITER_ROLE and PAUSER_ROLE; buyers, sellers, and assigned arbiters interact through role-checked and identity-checked lifecycle functions.",
            "The state machine is Funded -> Delivered -> Disputed, with terminal Released, Refunded, and Resolved. Delivery and dispute use strict before-deadline comparisons; timeout claims begin at the exact deadline. Settlement never sends ETH immediately; withdraw transfers each caller's credit under nonReentrant and checks-effects-interactions.",
            "Figure 1 shows the implemented on-chain and off-chain boundaries, participant roles, inherited OpenZeppelin controls, state machine, and pull-payment ledger.",
        ],
    )
    insert_picture_after(
        architecture_end,
        ROOT / "report" / "architecture_diagram.png",
        "Figure 1. SafeTrade architecture and trust boundaries.",
    )
    replace_section(
        by_heading,
        "2.2 User Roles and Access Control",
        [
            "Buyer: createEscrow (payable), confirmReceipt from Delivered or Disputed, raiseDispute during review, and claimRefundAfterDeadline after missed delivery.",
            "Seller: markDelivered before the delivery deadline, refundBySeller from Funded/Delivered/Disputed, and claimPaymentAfterReview at or after the review deadline.",
            "Assigned arbiter: resolveDispute only for its stored escrow. Role revocation after creation does not remove existing authority.",
            "Administrator: DEFAULT_ADMIN_ROLE for granting and revoking roles; no settlement or fund-redirect function.",
            "Pauser: PAUSER_ROLE pauses only createEscrow. Existing escrows and withdrawals remain usable.",
        ],
    )
    replace_section(
        by_heading,
        "2.3 Data and Process Design",
        [
            "Escrow stores buyer, seller, arbiter, amount, deliveryDeadline, reviewDeadline, state, termsHash, and deliveryHash. Mappings: escrows[id] and pendingWithdrawals[account]. Counters: nextEscrowId, totalLocked, and totalPending.",
            "Valid transitions: Funded->Delivered (seller marks delivery); Funded->Refunded (seller refund or buyer timeout); Delivered->Released (buyer confirm or seller timeout); Delivered->Refunded (seller refund); Delivered->Disputed (buyer dispute); Disputed->Released/Refunded/Resolved (buyer confirm, seller refund, or arbiter split).",
            "Accounting invariant: address(this).balance >= totalLocked + totalPending. Forced ETH may make the inequality strict and remains unallocated.",
        ],
    )
    replace_section(
        by_heading,
        "2.4 Technology Stack",
        [
            "Solidity 0.8.28; Cancun EVM; optimizer enabled with 200 runs; OpenZeppelin Contracts 5.6.1 [1]; Hardhat 2.29.2 [2]; ethers 6.17.0; Node.js 22; Solidity Coverage 0.8.17; Slither 0.11.6 [4]; Sepolia chain ID 11155111 [5]; Etherscan API V2 verification [6].",
            "Hardhat 2 was selected instead of the proposed Hardhat 3 line because solidity-coverage currently supports Hardhat 2, and coverage is a measurable project requirement. Compiler and bytecode settings remain those proposed. Python Web3 7.16.0 was used as a deployment fallback when Node RPC connectivity was unreliable. All package versions are pinned in package-lock.json or requirements.txt.",
        ],
    )
    replace_section(
        by_heading,
        "3.1 Contract Functionality",
        [
            "createEscrow validates funding, distinct nonzero participants, eligible arbiter, nonzero terms hash, and a one-hour to ninety-day delivery window. markDelivered stores evidence and starts a fixed three-day review. confirmReceipt, refundBySeller, claimRefundAfterDeadline, and claimPaymentAfterReview implement unilateral settlement under explicit state and deadline conditions.",
            "raiseDispute and resolveDispute implement arbitration. Only resolveDispute charges the 1% fee. withdraw sends accumulated credits. pause/unpause control admission. getEscrow returns a complete record and rejects unknown IDs.",
        ],
    )
    replace_section(
        by_heading,
        "3.2 Interface Description",
        [
            "The significant function interface is summarised in the table below. Access checks use stored identities for buyer/seller/assigned arbiter and OpenZeppelin roles for administration and pausing.",
        ],
    )
    replace_section(
        by_heading,
        "3.3 Important Implementation Decisions",
        [
            "Pull payments isolate recipients so one rejecting address cannot block others. Settlement credits pendingWithdrawals and updates totalLocked/totalPending before any later withdrawal.",
            "Fee calculation: fee = amount x 100 / 10,000; distributable = amount - fee; buyerAmount from buyerShareBps; sellerAmount = distributable - buyerAmount. Shares above 10,000 revert. One-wei tests confirm conserved value.",
            "Fixed arbiter assignment avoids administrator freezing through later role revocation. Pausing is admission control only. Ordinary receive/fallback ETH is rejected; forced ETH remains excess.",
        ],
    )
    code_end = replace_section(
        by_heading,
        "3.4 Representative Code Excerpts",
        [
            "Withdrawal uses checks-effects-interactions and nonReentrant: pendingWithdrawals[msg.sender] is zeroed and totalPending decreased before payable(msg.sender).call{value: amount}(\"\"). Failure reverts with TransferFailed and restores accounting.",
            "Dispute resolution derives sellerAmount by subtraction after the fee so rounding remainder cannot be trapped. Complete source is contracts/SafeTradeEscrow.sol in Appendix A of the submission package.",
        ],
    )
    code_end = insert_code_after(
        code_end,
        "Excerpt 1. Pull-payment withdrawal with checks-effects-interactions.",
        """function withdraw() external nonReentrant {
    uint256 amount = pendingWithdrawals[msg.sender];
    if (amount == 0) revert NothingToWithdraw();
    pendingWithdrawals[msg.sender] = 0;
    totalPending -= amount;
    (bool success, ) = payable(msg.sender).call{value: amount}("");
    if (!success) revert TransferFailed();
    emit Withdrawal(msg.sender, amount);
}""",
    )
    insert_code_after(
        code_end,
        "Excerpt 2. Arbitration fee and value-conserving split.",
        """uint256 fee = (amount * ARBITER_FEE_BPS) / BPS_DENOMINATOR;
uint256 distributable = amount - fee;
uint256 buyerAmount =
    (distributable * buyerShareBps) / BPS_DENOMINATOR;
uint256 sellerAmount = distributable - buyerAmount;""",
    )
    replace_section(
        by_heading,
        "4.1 Deployment Configuration",
        [
            "Network: Ethereum Sepolia (11155111). Compiler: Solidity 0.8.28. EVM: Cancun. Optimizer: enabled, 200 runs. Constructor argument: deployer/administrator address. OpenZeppelin Contracts 5.6.1 linked via npm. Secrets loaded from ignored .env.",
            "Because Hardhat's Node HTTP client timed out against available RPCs on the deployment machine, the identical compiled artifact was broadcast with Python Web3 7.16.0 (scripts/deploy_web3.py). Verification used Etherscan API V2 with Hardhat's Standard JSON input (scripts/verify_etherscan.py).",
        ],
    )
    replace_section(
        by_heading,
        "4.2 Deployment Information",
        [
            "Contract SafeTradeEscrow is recorded in the deployment table below. It was deployed in block 12147762 on 16 November 2026 at 21:57:12 HKT (13:57:12 UTC). The configured arbiter 0x9fFDd622766f99d71b17bD3c7fDB9259daABf9aA was granted ARBITER_ROLE in transaction 0x629f665d6a4460d969e3fbeb3e18a8e780dd8fa6f69c623f66321d3bbee22fc0.",
            "Normal flow (escrow 1): create 0x0d9fab02a029e9ba2ba8e5f223b607da2da1e372d1919c6379e349a1d0577dc6; delivery 0x717b4fffff1c9a851044277267540c4115d37fc9c8cf6f9204480edbe8280f69; release 0xe98a7ba81ea98922f164272516beb0a678395eebfba2480e967d06f560e04f4e; seller withdrawal 0x93ce10b0a9783039d9c26e109fd9169e36c2850f0d07f512b90397a03390f304.",
            "Disputed flow (escrow 2): the dedicated demo arbiter 0x4319B170EEeD1655d197AE1905B7735654034fFd was granted eligibility in 0xbbe58682ba9253de41b2c488e487eb376e659dce37a5c120345e69673c35d2df; create 0x9faf79d91dc339645cd95814f5d22f592d28ead9f6c9dc708ed73556de9fc2a7; delivery 0x88a3f4b23a0bf8428d621733c0c451eb0c8d2a4c20012be29d16c503c0c1eac3; dispute 0x2fc7d04454ee6986a31151da22c614c1943150df7101fdad841f4e2ae747da67; resolution 0x69dd163777fd21c032aa02f2db9b94e7b9ac5fe60eb5bd9866725c70e62d4b22; buyer and arbiter withdrawals 0x98423f3a1009d1b0ff063dc376fc834d0ab444525d10e5cac44e82f2748f0558 and 0x206f9172209d4b90d91926c6d4d5280aaabdac26b9337dd574f43a0ea4ffb2d1. Complete clickable links are in deployment/SEPOLIA_DEPLOYMENT.md.",
        ],
    )
    replace_section(
        by_heading,
        "4.3 Etherscan Verification",
        [
            "Verification settings matched deployment: compiler v0.8.28+commit.7893614a, optimizer 200 runs, Cancun EVM, constructor argument = deployer address, Standard JSON input from artifacts/build-info. Result: Pass - Verified.",
            "Verified source: https://sepolia.etherscan.io/address/0xf4D4eCc3420495000bbfE6719f22b8F3D8fdcf0E#code",
        ],
    )
    replace_section(
        by_heading,
        "5.1 Testing Environment",
        [
            "Framework: Hardhat 2.29.2 in-process network; ethers 6.17.0; Chai custom-error and event matchers; @nomicfoundation/hardhat-network-helpers for time control. Commands: npm test and npm run coverage. Synthetic hashes and test ETH only.",
        ],
    )
    replace_section(
        by_heading,
        "5.2 Test-Case Summary",
        [
            "61 automated tests passed across positive, negative, boundary, state, authorization, fee/split, one-wei, reentrancy, rejecting-recipient, forced-ETH, accounting, and pause categories. Production coverage: 100% statements/functions/lines and 98.72% branches. Representative cases are tabulated below; full records are in evidence/TEST_CASES.md.",
        ],
    )
    replace_section(
        by_heading,
        "5.3 Test Evidence",
        [
            "Primary evidence is executable: test/SafeTradeEscrow.test.js and coverage output. evidence/TEST_CASES.md records ID, purpose, preconditions, steps, expected result, actual result, and status. Local and Sepolia demo manifests are evidence/demo-hardhat.json and evidence/demo-sepolia.json. Screenshots alone are not relied upon.",
        ],
    )
    replace_section(
        by_heading,
        "6.1 Audit Scope and Methodology",
        [
            "Scope: contracts/SafeTradeEscrow.sol. Methods: manual review of authorization, CEI, reentrancy, deadlines, arithmetic, pause behaviour, and privacy; automated tests including malicious receivers; Slither 0.11.6 via npm run security (100 detectors). Raw output: evidence/slither-latest.json. Interpreted register: audit/SECURITY_REPORT.md.",
        ],
    )
    replace_section(
        by_heading,
        "6.2 Findings Summary",
        [
            "Slither reported zero High and zero Medium findings, five Low timestamp findings, and one Informational low-level-call finding. Manual review items ST-01 to ST-07 were mitigated by design and retested. Timestamp and low-level-call findings are accepted with justification in the findings table.",
        ],
    )
    replace_section(
        by_heading,
        "6.3 Manual Security Review",
        [
            "Controls reviewed: checks-effects-interactions; ReentrancyGuard on withdraw; stored-identity and role access control; input validation; terminal-state prevention of repeated settlement; pull-payment Ether handling; exact deadline comparisons; checked arithmetic; admission-only pause; and public-hash privacy limits.",
            "Residual risks: trusted/unavailable arbiter; revoked-but-assigned arbiter authority; approximate timestamps; public metadata; and private-key compromise. The contract is not claimed to be completely secure.",
        ],
    )
    replace_section(
        by_heading,
        "7.1 Conclusion",
        [
            "SafeTrade completes the required lifecycle for a focused escrow: design, implementation, comprehensive testing, security analysis, Sepolia deployment, source verification, and documented normal and disputed public flows. Its strongest properties are explicit state transitions, exact deadline semantics, restricted administrative power, independent pull payments, conserved accounting, and high automated coverage.",
            "The principal lessons learned were that precise state and deadline definitions simplify both implementation and boundary testing; pull payments isolate external-call failures; reproducible compiler settings must be preserved from deployment through verification; and automated analyzer output is useful only when interpreted against the actual threat model. Public-testnet work also showed the value of retaining recoverable test accounts and providing a second RPC-compatible deployment route.",
        ],
    )
    replace_section(
        by_heading,
        "7.2 Future Work",
        [
            "Realistic improvements include mutually authorized arbiter replacement, multi-signature or decentralized arbitration, ERC-20 support with safe token handling, signed off-chain terms packages, and a minimal interface that independently recomputes and displays hashes before signing.",
        ],
    )
    replace_section(
        by_heading,
        "References",
        [
            "[1] OpenZeppelin, \"OpenZeppelin Contracts 5.x Documentation,\" https://docs.openzeppelin.com/contracts/5.x/ (accessed Nov 2026).",
            "[2] Nomic Foundation, \"Hardhat Documentation,\" https://hardhat.org/docs (accessed Nov 2026).",
            "[3] Solidity Team, \"Solidity 0.8.28 Documentation: Security Considerations,\" https://docs.soliditylang.org/en/v0.8.28/security-considerations.html (accessed Nov 2026).",
            "[4] Trail of Bits / Crytic, \"Slither, the Solidity Source Analyzer,\" https://github.com/crytic/slither (accessed Nov 2026).",
            "[5] Ethereum Foundation, \"Ethereum Test Networks,\" https://ethereum.org/en/developers/docs/networks/ (accessed Nov 2026).",
            "[6] Etherscan, \"Contract Verification,\" https://docs.etherscan.io/ (accessed Nov 2026).",
            "[7] AI assistance: Cursor AI helped structure implementation and documentation. The author remains responsible for correctness, security decisions, and explainability.",
        ],
    )
    replace_section(
        by_heading,
        "Appendix A: Complete Solidity Source Code",
        [
            "Complete production source: contracts/SafeTradeEscrow.sol. Test helpers used only in local security tests: contracts/test/WithdrawalReceiver.sol and contracts/test/ForceSender.sol. Do not treat test helpers as production deployment targets.",
        ],
    )
    replace_section(
        by_heading,
        "Appendix B: Deployment Scripts and Configuration",
        [
            "scripts/deploy.js and scripts/demo.js (Hardhat); scripts/deploy_web3.py, scripts/verify_etherscan.py, and scripts/demo_web3.py (Python fallback); hardhat.config.js; .env.example; deployments/sepolia.json; deployment/SEPOLIA_DEPLOYMENT.md.",
        ],
    )
    replace_section(
        by_heading,
        "Appendix C: Test Code and Selected Outputs",
        [
            "Executable tests: test/SafeTradeEscrow.test.js. Case record: evidence/TEST_CASES.md. Result summary: 61 passing; production coverage 100% lines / 98.72% branches. Local demo: evidence/demo-hardhat.json.",
        ],
    )
    replace_section(
        by_heading,
        "Appendix D: Security-Analysis Output",
        [
            "Interpreted report: audit/SECURITY_REPORT.md. Raw Slither JSON: evidence/slither-latest.json. Command: npm run security (Slither 0.11.6).",
        ],
    )
    replace_section(
        by_heading,
        "Appendix E: Etherscan and Transaction Evidence",
        [
            "Verified contract: https://sepolia.etherscan.io/address/0xf4D4eCc3420495000bbfE6719f22b8F3D8fdcf0E#code. Deployment tx: 0x6311661fc5b586ee4ac5ccf58c99f498ef5f691304e785c407bd8a42be3d045a (block 12147762). Public flow receipts: evidence/demo-sepolia.json.",
        ],
    )
    replace_section(
        by_heading,
        "Appendix F: Additional Diagrams or Metadata",
        [
            "Architecture diagram: report/architecture_diagram.png. State-transition diagram: Proposal/escrow_state_diagram.png. Proposal design document: Proposal/CSIT5760_Project_Proposal.md. No confidential personal data or production credentials are included.",
        ],
    )

    tables = {
        tuple(cell.text.strip() for cell in table.rows[0].cells): table
        for table in document.tables
    }

    interface = tables.get(
        ("Item", "Caller / access", "Inputs / outputs", "State change / event", "Revert conditions")
    )
    if interface is not None:
        fill_table(
            interface,
            [
                [
                    "createEscrow",
                    "Buyer; whenNotPaused",
                    "seller, arbiter, deadline, termsHash + msg.value -> escrowId",
                    "Funded; EscrowCreated; totalLocked += amount",
                    "ZeroAmount, InvalidAddress, InvalidHash, NotAuthorized, window errors, EnforcedPause",
                ],
                [
                    "markDelivered",
                    "Seller",
                    "escrowId, deliveryHash",
                    "Delivered; reviewDeadline set; DeliveryMarked",
                    "NotAuthorized, InvalidState, DeliveryDeadlinePassed, InvalidHash",
                ],
                [
                    "confirmReceipt",
                    "Buyer",
                    "escrowId",
                    "Released; seller credited; PaymentReleased",
                    "NotAuthorized, InvalidState",
                ],
                [
                    "raiseDispute",
                    "Buyer",
                    "escrowId",
                    "Disputed; DisputeRaised",
                    "NotAuthorized, InvalidState, ReviewDeadlinePassed",
                ],
                [
                    "refundBySeller",
                    "Seller",
                    "escrowId",
                    "Refunded; buyer credited; EscrowRefunded",
                    "NotAuthorized, InvalidState",
                ],
                [
                    "claimRefundAfterDeadline",
                    "Buyer",
                    "escrowId",
                    "Refunded; buyer credited; EscrowRefunded",
                    "NotAuthorized, InvalidState, DeliveryDeadlineNotReached",
                ],
                [
                    "claimPaymentAfterReview",
                    "Seller",
                    "escrowId",
                    "Released; seller credited; PaymentReleased",
                    "NotAuthorized, InvalidState, ReviewDeadlineNotReached",
                ],
                [
                    "resolveDispute",
                    "Assigned arbiter",
                    "escrowId, buyerShareBps",
                    "Resolved; split credits + 1% fee; DisputeResolved",
                    "NotAuthorized, InvalidState, InvalidShare",
                ],
                [
                    "withdraw",
                    "Any credited account; nonReentrant",
                    "none -> ETH transfer",
                    "pending/totalPending cleared; Withdrawal",
                    "NothingToWithdraw, TransferFailed",
                ],
                [
                    "pause / unpause",
                    "PAUSER_ROLE",
                    "none",
                    "Admission toggled; Paused / Unpaused",
                    "AccessControl error, EnforcedPause, ExpectedPause",
                ],
                [
                    "getEscrow",
                    "Any caller; view",
                    "escrowId -> Escrow",
                    "No state change",
                    "EscrowNotFound",
                ],
            ],
        )

    settings = tables.get(("Setting", "Value"))
    if settings is not None:
        fill_table(
            settings,
            [
                ["Network / chain ID", "Ethereum Sepolia / 11155111"],
                ["Contract", "SafeTradeEscrow"],
                ["Compiler", "Solidity 0.8.28 (+commit.7893614a)"],
                ["Optimizer / EVM", "enabled, 200 runs / Cancun"],
                ["OpenZeppelin", "5.6.1"],
                ["Deployer", "0x84773c4dA4B711f38a0Fe524Fad5Ed07bb0C6F4E"],
                ["Deployment time", "16 Nov 2026, 21:57:12 HKT / 13:57:12 UTC"],
                ["Deployment method", "Python Web3 7.16.0 using Hardhat artifact"],
                ["Constructor argument", "deployer/administrator address"],
            ],
        )

    deployment = tables.get(("Contract", "Address", "Tx hash / block", "Verified URL"))
    if deployment is not None:
        fill_table(
            deployment,
            [
                [
                    "SafeTradeEscrow",
                    "0xf4D4eCc3420495000bbfE6719f22b8F3D8fdcf0E",
                    "0x6311661fc5b586ee4ac5ccf58c99f498ef5f691304e785c407bd8a42be3d045a / 12147762",
                    "https://sepolia.etherscan.io/address/0xf4D4eCc3420495000bbfE6719f22b8F3D8fdcf0E#code",
                ],
            ],
        )

    tests = tables.get(("Test ID", "Purpose / precondition", "Steps / input", "Expected / actual", "Status"))
    if tests is not None:
        fill_table(
            tests,
            [
                ["TC-01", "Create escrow; eligible arbiter", "Buyer funds 1 ETH", "Observed Funded, EscrowCreated, totalLocked=1 ETH", "Pass"],
                ["TC-12", "Delivery at deadline", "Seller marks at exact deadline", "Observed DeliveryDeadlinePassed; state stayed Funded", "Pass"],
                ["TC-13", "Buyer timeout", "Claim at exact delivery deadline", "Observed Refunded and buyer credit=1 ETH", "Pass"],
                ["TC-14", "Normal release", "Buyer confirms delivery", "Observed Released and seller credit=1 ETH", "Pass"],
                ["TC-20", "Arbiter 25/75 split", "resolveDispute(2500)", "Observed 1% fee; three credits summed to 1 ETH", "Pass"],
                ["TC-28", "Recursive receiver", "Receive re-enters withdraw", "Observed receiveCount=1; pending credit=0", "Pass"],
                ["TC-31", "Pause admission", "Pause then settle existing", "Observed EnforcedPause on create; settlement/withdraw succeeded", "Pass"],
                ["TC-35", "Unauthorized role admin", "Non-admin grants role", "Observed AccessControlUnauthorizedAccount", "Pass"],
            ],
        )

    findings = tables.get(("ID / severity", "Finding and impact", "Affected code", "Remediation", "Status / retest"))
    if findings is not None:
        fill_table(
            findings,
            [
                ["ST-01 / High-impact threat", "Reentrant/repeated withdrawal could duplicate a credit", "withdraw, lines 261-270", "CEI, zero credit, decrease liability, nonReentrant", "Resolved by design; recursive receiver Pass"],
                ["ST-02 / Medium-impact threat", "Rejecting recipient could block settlement", "settlement/withdraw, lines 190-270", "Independent pull-payment credits", "Mitigated; rejecting receiver preserves only its credit"],
                ["ST-03 / High-impact threat", "Unsupported or repeated state transition could double-settle", "lifecycle functions, lines 146-257", "Exact source-state checks and terminal states", "Resolved; wrong-state/repeat tests Pass"],
                ["ST-04 / High-impact threat", "Unauthorized caller could redirect settlement", "roles/lifecycle, lines 91-278", "Stored identities plus AccessControl", "Resolved; unauthorized-caller tests Pass"],
                ["ST-05 / Medium-impact threat", "Ambiguous deadline boundary could enable both parties", "deadline functions, lines 146-233", "Strict < for action; >= for timeout", "Resolved; before/exact boundary tests Pass"],
                ["ST-06 / Medium-impact threat", "Fee/split rounding could over-credit or trap value", "resolveDispute, lines 239-257", "Share cap and seller amount by subtraction", "Resolved; 0/10000/10001 bps and 1-wei tests Pass"],
                ["ST-07 / Medium-impact threat", "Pauser could freeze refunds and withdrawals", "pause controls, lines 272-278", "Pause applies only to createEscrow", "Resolved; existing settlement/withdraw while paused Pass"],
                ["ST-08 / Low accepted", "Validator can slightly influence deadline timestamps", "deadline comparisons", "Hour/day windows and explicit boundaries", "Accepted; boundary tests Pass"],
                ["ST-09 / Informational accepted", "Low-level ETH call is externally controlled", "withdraw, line 267", "Intentional pull payment; check success; CEI", "Accepted; success/reject/reentry tests Pass"],
            ],
        )

    clear_guidance_tables(document)

    for paragraph in document.paragraphs:
        if paragraph.text.startswith("\u2610"):
            set_runs(paragraph, paragraph.text.replace("\u2610", "\u2611", 1))

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    document.save(OUTPUT)
    print(f"Wrote {OUTPUT}")


if __name__ == "__main__":
    main()
