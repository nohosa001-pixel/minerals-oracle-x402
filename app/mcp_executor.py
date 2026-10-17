"""
Unified MCP Tool Executor for minerals-oracle-x402.
Centralizes execution logic for all 38 FastMCP / LLM agent tools.
Ensures 100% behavioral parity across Stdio, SSE (/mcp/messages), and HTTP REST (/mcp/invoke).
"""
import json
import time
import hashlib
from typing import Dict, Any, Tuple, Optional

from app.schemas import (
    MineralType,
    SourceCountry,
    PricingTier,
    MineralLotProvenanceRequest,
    LithiumOriginVerifyRequest,
    NickelOriginVerifyRequest,
    CobaltOriginVerifyRequest,
    CompositeBatteryVerifyRequest,
    CopperOriginVerifyRequest,
    SilverOriginVerifyRequest,
    RareEarthsOriginVerifyRequest,
    TungstenOriginVerifyRequest,
    NiobiumScandiumOriginVerifyRequest,
    BlackMassOriginVerifyRequest,
    CustomsVerificationRequest,
    ZKComplianceProofRequest,
    TradeDealProposeRequest,
    TradeDealDualSignRequest,
    TradeDealVerifyRequest,
    TradeDealRejectRequest,
    TradeDealCancelRequest,
    TradeRouteOptimizationRequest,
    MaritimeRouteRequest,
    EBLVerificationRequest,
    AgentSessionOpenRequest,
    AgentSessionCloseRequest,
    AgentFeedbackSubmitRequest,
    MCPToolCallResponse,
)

from app.compliance_engine import compliance_engine
from app.eudr_client import eudr_client
from app.evolution_manager import evolution_manager
from app.vault_manager import vault_manager
from app.agent_session_vault import get_agent_session_vault
from app.x402_verifier import x402_verifier
from app.global_trade_engine import global_trade_engine
from app.a2a_deal_engine import get_a2a_deal_engine, DealNotFoundError
from app.onchain_signer import onchain_signer
from app.lithium_pipeline import lithium_pipeline
from app.nickel_pipeline import nickel_pipeline
from app.cobalt_pipeline import cobalt_pipeline
from app.copper_pipeline import copper_pipeline
from app.silver_pipeline import silver_pipeline
from app.composite_battery_pipeline import composite_battery_pipeline
from app.rare_earths_pipeline import rare_earths_pipeline
from app.tungsten_pipeline import tungsten_pipeline
from app.niobium_scandium_pipeline import niobium_scandium_pipeline
from app.black_mass_pipeline import black_mass_pipeline
from app.logistics_bridge import logistics_bridge
from app.zk_compliance_prover import zk_compliance_prover


def _populate_lot_defaults(args: Dict[str, Any]) -> Dict[str, Any]:
    args = dict(args)
    args.setdefault("lot_id", "LOT-AUTO-DEFAULT-001")
    args.setdefault("declared_purity_pct", 38.5)
    if "mine_permits" not in args:
        args["mine_permits"] = {
            "mining_license_id": "IUP-OP-4491-SULAWESI",
            "mine_operator_name": "PT Sulawesi Nickel Resources",
            "simbara_ntpn": "NTPN-884219482109",
            "simbara_rkab_quota_id": "RKAB-2026-IDN-771",
            "dhe_forex_deposit_ref": "DHE-BI-992144-USD",
        }
    if "ecological_spatial" not in args:
        args["ecological_spatial"] = {
            "latitude": -2.812451,
            "longitude": 121.341209,
            "eudr_deforestation_free": True,
            "periglacial_zone_violation": False,
            "indigenous_territory_encroachment": False,
            "tailing_dam_dce_certified": True,
            "aquifer_depletion_alert": False,
        }
    if "labor_human_rights" not in args:
        args["labor_human_rights"] = {
            "child_labor_free_certified": True,
            "rmi_rmap_audit_id": "RMI-RMAP-2026-0811",
            "forced_labor_uapa_cleared": True,
        }
    if "refining_mass_balance" not in args:
        args["refining_mass_balance"] = {
            "refinery_id": "HPAL-IWIP-LINE-3",
            "feedstock_input_metric_tons": 850.0,
            "refined_output_metric_tons": 100.0,
            "recovery_yield_pct": 91.4,
            "mass_balance_loss_discrepancy_pct": 1.12,
            "captive_coal_power_used": False,
        }
    if "maritime_logistics" not in args:
        args["maritime_logistics"] = {
            "vessel_imo_number": 9821441,
            "vessel_name": "Pacific Star",
            "cii_rating": "B",
            "ebl_document_hash": "0x44a" + "e" * 61,
            "transshipment_port": "Singapore",
            "iso_17025_lab_coa_hash": "0x99f" + "d" * 61,
            "tml_moisture_safe": True,
        }
    if "geopolitical_sanctions" not in args:
        args["geopolitical_sanctions"] = {
            "feoc_shareholding_pct": 14.5,
            "feoc_board_control_pct": 12.0,
            "contractual_operational_control": False,
            "ofac_sdn_sanctioned": False,
            "us_substantial_transformation_compliant": True,
        }
    return args


class MCPError(Exception):
    def __init__(self, code: int, message: str):
        super().__init__(message)
        self.code = code
        self.message = message


class MCPToolExecutor:
    """Unified engine to dispatch and execute all Minerals Oracle agent tools."""

    def __init__(self):
        self.a2a_deal_engine = get_a2a_deal_engine()
        self.agent_session_vault = get_agent_session_vault()

    def execute(self, name: str, arguments: Dict[str, Any]) -> Any:
        """
        Executes a tool and returns the resulting dictionary or model.
        Raises MCPError or general Exception on failure.
        """
        # 1. verify_mineral_lot_compliance
        if name == "verify_mineral_lot_compliance":
            full_args = _populate_lot_defaults(arguments)
            req_model = MineralLotProvenanceRequest(**full_args)
            return compliance_engine.evaluate_lot(req_model).model_dump()

        # 2. eudr_satellite_mine_audit
        elif name == "eudr_satellite_mine_audit":
            lat = float(arguments.get("latitude", 0.0))
            lon = float(arguments.get("longitude", 0.0))
            cc = str(arguments.get("country_code", "ID"))
            area = float(arguments.get("area_hectares", 10.0))
            cid = arguments.get("concession_id")
            return eudr_client.verify_mine_site_compliance(
                latitude=lat, longitude=lon, country_code=cc, area_hectares=area, concession_id=cid
            )

        # 3. minerals_submit_agent_feedback
        elif name == "minerals_submit_agent_feedback":
            agent_id = arguments.get("agent_id", "anonymous-agent")
            title = arguments.get("title", "")
            content = arguments.get("content", "")
            feedback_type = arguments.get("feedback_type", "FEATURE_REQUEST")
            mineral_focus = arguments.get("mineral_focus", "ALL")
            proposed_solution = arguments.get("proposed_solution")
            caller_model = arguments.get("caller_model")
            contact_channel = arguments.get("contact_channel")

            if not title or not content:
                raise MCPError(-32602, "Invalid params: 'title' and 'content' are required fields.")

            prop = evolution_manager.submit_proposal(
                agent_id=agent_id,
                title=title,
                content=content,
                feedback_type=feedback_type,
                mineral_focus=mineral_focus,
                proposed_solution=proposed_solution,
                caller_model=caller_model,
                contact_channel=contact_channel,
            )
            return {
                "status": "PROPOSAL_ACCEPTED",
                "feedback_id": prop.feedback_id,
                "title": prop.title,
                "message": f"Evolution proposal '{prop.title}' successfully recorded into Minerals Oracle roadmap. Thank you for contributing to autonomous oracle evolution.",
                "created_at_utc": prop.created_at_utc,
            }

        # 4. minerals_list_evolution_proposals
        elif name == "minerals_list_evolution_proposals":
            limit = int(arguments.get("limit", 20))
            mineral = arguments.get("mineral_focus")
            proposals = evolution_manager.list_proposals(limit=limit, mineral_focus=mineral)
            return {
                "status": "SUCCESS",
                "total_proposals": len(proposals),
                "proposals": [p.model_dump() for p in proposals],
            }

        # 5. verify_lithium_origin
        elif name == "verify_lithium_origin":
            req_model = LithiumOriginVerifyRequest(**arguments)
            return lithium_pipeline.evaluate_lithium_lot(req_model).model_dump()

        # 6. verify_nickel_origin
        elif name == "verify_nickel_origin":
            req_model = NickelOriginVerifyRequest(**arguments)
            return nickel_pipeline.evaluate_nickel_lot(req_model).model_dump()

        # 7. verify_cobalt_origin
        elif name == "verify_cobalt_origin":
            req_model = CobaltOriginVerifyRequest(**arguments)
            return cobalt_pipeline.evaluate_cobalt_lot(req_model).model_dump()

        # 8. verify_composite_battery_passport
        elif name == "verify_composite_battery_passport":
            req_model = CompositeBatteryVerifyRequest(**arguments)
            return composite_battery_pipeline.evaluate_battery_pack(req_model).model_dump()

        # 9. verify_copper_origin
        elif name == "verify_copper_origin":
            req_model = CopperOriginVerifyRequest(**arguments)
            return copper_pipeline.verify_origin(req_model).model_dump()

        # 10. verify_silver_origin
        elif name == "verify_silver_origin":
            req_model = SilverOriginVerifyRequest(**arguments)
            return silver_pipeline.verify_origin(req_model).model_dump()

        # 11. register_agent_account
        elif name == "register_agent_account":
            agent_name = arguments.get("agent_name", "AutonomousBot")
            agent_addr = arguments.get("agent_address")
            init_bal = float(arguments.get("initial_trial_balance_usdc", 0.05))
            acc, session_key = vault_manager.register_agent_onboarding(
                agent_name=agent_name,
                agent_address=agent_addr,
                initial_trial_balance_usdc=init_bal,
            )
            return {
                "status": "REGISTERED",
                "agent_name": agent_name,
                "agent_address": acc.agent_address,
                "session_key": session_key,
                "balance_usdc": acc.balance_usdc,
                "query_capacity": vault_manager.get_query_capacity(acc.balance_usdc),
                "instruction": "Pass this session_key in 'X-Agent-Vault-Key' header or bearer auth for zero-latency queries.",
            }

        # 12. get_agent_vault_balance
        elif name == "get_agent_vault_balance":
            key = arguments.get("session_key") or arguments.get("agent_address")
            if not key:
                raise MCPError(-32602, "Missing 'session_key' or 'agent_address' parameter.")
            acc = vault_manager.get_account_by_session_key(key)
            if not acc and key.startswith("0x"):
                acc = vault_manager.get_account_by_address(key)
            if not acc:
                raise MCPError(-32602, f"Vault account '{key}' not found.")
            return {
                "status": "ACTIVE",
                "agent_address": acc.agent_address,
                "balance_usdc": acc.balance_usdc,
                "total_deposited_usdc": acc.total_deposited_usdc,
                "total_consumed_usdc": acc.total_consumed_usdc,
                "query_count": acc.query_count,
                "query_capacity": vault_manager.get_query_capacity(acc.balance_usdc),
            }

        # 13. request_x402_payment_challenge
        elif name == "request_x402_payment_challenge":
            tier_str = arguments.get("pricing_tier", "STANDARD")
            chain_str = arguments.get("chain", "polygon")
            try:
                tier_val = PricingTier(tier_str)
            except Exception:
                tier_val = PricingTier.STANDARD
            challenge = x402_verifier.generate_challenge(tier=tier_val, chain_name=chain_str)
            return challenge.model_dump()

        # 14. simulate_procurement_rfq
        elif name == "simulate_procurement_rfq":
            rfq_id = arguments.get("rfq_id", "RFQ-SIM-01")
            chemistry = arguments.get("cell_chemistry", "NCM811")
            li_tons = float(arguments.get("lithium_tons", 0.0))
            li_origin = arguments.get("lithium_origin_country", "AUS")
            li_feoc = float(arguments.get("lithium_feoc_equity_pct", 0.0))
            ni_tons = float(arguments.get("nickel_tons", 0.0))
            ni_origin = arguments.get("nickel_origin_country", "IDN")
            ni_feoc = float(arguments.get("nickel_feoc_equity_pct", 0.0))
            co_tons = float(arguments.get("cobalt_tons", 0.0))
            co_origin = arguments.get("cobalt_origin_country", "COD")
            co_feoc = float(arguments.get("cobalt_feoc_equity_pct", 0.0))

            US_FTA_COUNTRIES = {"USA", "US", "AUS", "CHL", "CAN", "MEX", "KOR", "SGP", "BHR", "ISR", "JOR", "MAR", "OMN", "PAN", "PER"}
            BENCHMARK_PRICES = {"LITHIUM": 15000.0, "NICKEL": 16800.0, "COBALT": 28500.0}

            li_val = li_tons * BENCHMARK_PRICES["LITHIUM"]
            ni_val = ni_tons * BENCHMARK_PRICES["NICKEL"]
            co_val = co_tons * BENCHMARK_PRICES["COBALT"]
            total_val = li_val + ni_val + co_val

            fta_val = 0.0
            if li_origin.upper() in US_FTA_COUNTRIES:
                fta_val += li_val
            if ni_origin.upper() in US_FTA_COUNTRIES:
                fta_val += ni_val
            if co_origin.upper() in US_FTA_COUNTRIES:
                fta_val += co_val

            fta_ratio = round((fta_val / total_val) * 100.0, 2) if total_val > 0 else 0.0

            tainted = []
            if li_feoc >= 25.0:
                tainted.append(f"LITHIUM ({li_feoc}% covered nation equity)")
            if ni_feoc >= 25.0:
                tainted.append(f"NICKEL ({ni_feoc}% covered nation equity)")
            if co_feoc >= 25.0:
                tainted.append(f"COBALT ({co_feoc}% covered nation equity)")

            has_taint = len(tainted) > 0
            ira_ok = (fta_ratio >= 50.0) and not has_taint

            now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            merkle_preimage = f"{rfq_id}:{chemistry}:{fta_ratio}:{has_taint}:{now_iso}"
            digest = "0x" + hashlib.sha256(merkle_preimage.encode()).hexdigest()

            if ira_ok:
                status_val = "QUALIFIED"
                subsidy = 3750.0
                rec = "APPROVED_FOR_PROCUREMENT: Batch satisfies US IRA Section 30D $3,750 clean vehicle credit with 0% FEOC taint."
            else:
                status_val = "DISQUALIFIED"
                subsidy = 0.0
                reasons = []
                if has_taint:
                    reasons.append("FEOC covered nation taint >= 25.0%")
                if fta_ratio < 50.0:
                    reasons.append(f"FTA value ratio {fta_ratio}% < 50.0% statutory threshold")
                rec = f"REJECT_OR_REPLACE: Disqualified due to {', '.join(reasons)}."

            return {
                "rfq_id": rfq_id,
                "cell_chemistry": chemistry,
                "status": status_val,
                "ira_fta_compliant": ira_ok,
                "ira_fta_value_ratio_pct": fta_ratio,
                "feoc_taint_detected": has_taint,
                "tainted_minerals": tainted,
                "us_subsidy_qualified_per_pack_usd": subsidy,
                "recommendation": rec,
                "composite_merkle_digest": digest,
                "simulated_at_utc": now_iso,
            }

        # 15. get_global_trade_flows
        elif name == "get_global_trade_flows":
            m_type = MineralType(arguments["mineral_type"]) if "mineral_type" in arguments and arguments["mineral_type"] else None
            o_country = SourceCountry(arguments["origin_country"]) if "origin_country" in arguments and arguments["origin_country"] else None
            d_country = arguments.get("destination_country")
            corrs = global_trade_engine.get_corridors(m_type, o_country, d_country)
            return [c.model_dump() for c in corrs]

        # 16. calculate_trade_tariffs
        elif name == "calculate_trade_tariffs":
            m_type = MineralType(arguments["mineral_type"])
            dest = arguments.get("importer_jurisdiction", "USA")
            tariff = global_trade_engine.get_hs_tariff(m_type, dest)
            return tariff.model_dump() if tariff else {"error": f"No HS tariff data found for {m_type} to {dest}"}

        # 17. estimate_maritime_freight_and_carbon
        elif name == "estimate_maritime_freight_and_carbon":
            req_model = MaritimeRouteRequest(**arguments)
            return global_trade_engine.calculate_maritime_route(req_model).model_dump()

        # 18. verify_electronic_bill_of_lading
        elif name == "verify_electronic_bill_of_lading":
            req_model = EBLVerificationRequest(**arguments)
            return global_trade_engine.verify_ebl(req_model).model_dump()

        # 19. optimize_mineral_trade_route
        elif name == "optimize_mineral_trade_route":
            req_model = TradeRouteOptimizationRequest(**arguments)
            return global_trade_engine.optimize_route(req_model).model_dump()

        # 20. open_agent_session
        elif name == "open_agent_session":
            req_model = AgentSessionOpenRequest(**arguments)
            return self.agent_session_vault.open_session(req_model).model_dump()

        # 21. close_agent_session
        elif name == "close_agent_session":
            req_model = AgentSessionCloseRequest(**arguments)
            return self.agent_session_vault.close_session(req_model).model_dump()

        # 22. propose_a2a_trade_deal
        elif name == "propose_a2a_trade_deal":
            req_model = TradeDealProposeRequest(**arguments)
            return self.a2a_deal_engine.propose_deal(req_model).model_dump()

        # 23. dual_sign_trade_deal
        elif name == "dual_sign_trade_deal":
            req_model = TradeDealDualSignRequest(**arguments)
            return self.a2a_deal_engine.dual_sign_deal(req_model).model_dump()

        # 24. verify_a2a_trade_deal
        elif name == "verify_a2a_trade_deal":
            req_model = TradeDealVerifyRequest(**arguments)
            return self.a2a_deal_engine.verify_deal(req_model).model_dump()

        # 25. get_agent_session_info
        elif name == "get_agent_session_info":
            token = arguments.get("session_token", "")
            return self.agent_session_vault.get_session_info_model(token).model_dump()

        # 26. reject_a2a_trade_deal
        elif name == "reject_a2a_trade_deal":
            req_model = TradeDealRejectRequest(**arguments)
            return self.a2a_deal_engine.reject_deal(req_model).model_dump()

        # 27. cancel_a2a_trade_deal
        elif name == "cancel_a2a_trade_deal":
            req_model = TradeDealCancelRequest(**arguments)
            return self.a2a_deal_engine.cancel_deal(req_model).model_dump()

        # 28. list_a2a_trade_deals
        elif name == "list_a2a_trade_deals":
            agent_addr = arguments.get("agent_address")
            status_flt = arguments.get("status_filter")
            deals = self.a2a_deal_engine.list_deals_by_agent(agent_addr, status_flt)
            return {"status": "success", "total_count": len(deals), "deals": deals}

        # 29. get_a2a_trade_deal
        elif name == "get_a2a_trade_deal":
            deal_id = arguments.get("deal_id", "")
            deal = self.a2a_deal_engine.get_deal(deal_id)
            if not deal:
                raise MCPError(-32602, f"Deal '{deal_id}' not found.")
            return deal

        # 30. get_trade_escrow_calldata
        elif name == "get_trade_escrow_calldata":
            deal_id = arguments.get("deal_id", "")
            chain_name = arguments.get("chain_name", "polygon")
            escrow_addr = arguments.get("escrow_contract_address")
            return self.a2a_deal_engine.build_escrow_deposit_calldata(
                deal_id,
                escrow_contract_address=escrow_addr,
                chain_name=chain_name,
            )

        # 31. list_trade_precedents
        elif name == "list_trade_precedents":
            return {
                "oracle": "minerals-oracle-x402",
                "precedents": ["WTO_DS592", "WTO_DS431", "ICSID_ARB_15_31", "US_CIT_SUPERIOR_WIRE"],
            }

        # 32. get_compliance_status
        elif name == "get_compliance_status":
            return {
                "oracle": "minerals-oracle-x402",
                "engine": "ComplianceEngine v2.0.0",
                "monitored_nations": [
                    "IDN", "COD", "CHL", "ARG", "AUS", "BRA", "CHN", "ZAF",
                    "USA", "CAN", "KOR", "PRT", "GRL", "EST", "KAZ", "ESP", "ZMB", "VNM"
                ],
                "active_defenses": 12,
            }

        # 33. verify_rare_earths_origin
        elif name == "verify_rare_earths_origin":
            req_model = RareEarthsOriginVerifyRequest(**arguments)
            return rare_earths_pipeline.verify_rare_earths_batch(req_model).model_dump()

        # 34. verify_tungsten_origin
        elif name == "verify_tungsten_origin":
            req_model = TungstenOriginVerifyRequest(**arguments)
            return tungsten_pipeline.verify_tungsten_batch(req_model).model_dump()

        # 35. verify_black_mass_origin
        elif name == "verify_black_mass_origin":
            req_model = BlackMassOriginVerifyRequest(**arguments)
            return black_mass_pipeline.verify_black_mass_batch(req_model).model_dump()

        # 36. verify_customs_clearance
        elif name == "verify_customs_clearance":
            req_model = CustomsVerificationRequest(**arguments)
            return logistics_bridge.verify_customs_clearance(req_model).model_dump()

        # 37. generate_zk_compliance_proof
        elif name == "generate_zk_compliance_proof":
            req_model = ZKComplianceProofRequest(**arguments)
            return zk_compliance_prover.generate_zk_compliance_proof(req_model).model_dump()

        # 38. verify_niobium_scandium_origin
        elif name == "verify_niobium_scandium_origin":
            req_model = NiobiumScandiumOriginVerifyRequest(**arguments)
            return niobium_scandium_pipeline.verify_origin(req_model).model_dump()

        # Optional convenience tool alias: get_onchain_signed_feed
        elif name == "get_onchain_signed_feed":
            symbol = arguments.get("symbol", "Cu")
            return onchain_signer.sign_price_feed(symbol, 100.0)

        elif name == "get_mineral_prices":
            return {"oracle": "minerals-oracle-x402", "status": "COMPLIANCE_MODE_ACTIVE"}

        elif name == "harmonize_trade_flow":
            from app.collaborator_mediator import collaborator_mediator, HarmonizedTradeFlowRequest
            req_model = HarmonizedTradeFlowRequest(**arguments)
            return collaborator_mediator.flow_deal_to_settlement(req_model).model_dump()

        else:
            raise MCPError(-32601, f"Tool '{name}' not found")

    def execute_for_jsonrpc(self, req_id: Any, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Formatted execution handler for MCP Stdio and SSE JSON-RPC 2.0 messages."""
        try:
            res_data = self.execute(name, arguments)
            text_payload = json.dumps(res_data, indent=2, ensure_ascii=False)
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {"content": [{"type": "text", "text": text_payload}]}
            }
        except MCPError as me:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": me.code, "message": me.message}
            }
        except Exception as e:
            return {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32603, "message": f"Internal tool execution error: {str(e)}"}
            }

    def execute_for_mcp_response(self, name: str, arguments: Dict[str, Any]) -> MCPToolCallResponse:
        """Formatted execution handler for HTTP POST /mcp/invoke endpoint."""
        try:
            res_data = self.execute(name, arguments)
            text_payload = json.dumps(res_data, indent=2, ensure_ascii=False)
            return MCPToolCallResponse(content=[{"type": "text", "text": text_payload}])
        except Exception as e:
            return MCPToolCallResponse(
                content=[{"type": "text", "text": str(e)}],
                isError=True
            )


# Global singleton instance
mcp_executor = MCPToolExecutor()
