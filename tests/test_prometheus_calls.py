from unittest import TestCase, mock
from unittest.mock import ANY, MagicMock, call
from uuid import uuid4

import pendulum
from app.exports.agents.bases.base import AgentExportData, AgentExportDataOutput
from app.exports.agents.wasabi import Wasabi as export_wasabi


class TestExportWasabiPrometheusCalls(TestCase):
    @mock.patch("app.exports.agents.wasabi.atlas")
    @mock.patch("app.exports.agents.wasabi.Wasabi.config")
    def test_send_export_data_receipt_number_not_found(self, mock_config, mock_atlas) -> None:
        """
        Test that a ReceiptNumberNotFound exception raised from export() calls the expected prometheus metrics
        """

        # GIVEN
        wasabi = export_wasabi()
        agent_export_data = AgentExportData(
            outputs=[AgentExportDataOutput("export.json", {"origin_id": uuid4(), "ReceiptNo": None})],
            transactions=[],
            extra_data={},
        )
        mock_session = MagicMock()
        mock_retry_count = 3
        expected_counter_calls = [
            call(
                agent=wasabi,
                counter_name="receipt_number_not_found",
                increment_by=1,
                process_type="export",
                slug=wasabi.provider_slug,
                retry_count=mock_retry_count,
            ),
        ]

        # WHEN
        with mock.patch.object(wasabi, "bink_prometheus"):
            with mock.patch.object(wasabi, "get_retry_datetime") as mock_get_retry_datetime:
                with mock.patch.object(wasabi, "api_class") as mock_api_class:
                    mock_get_retry_datetime.return_value = pendulum.now("UTC")
                    mock_api = MagicMock()
                    mock_response = MagicMock()
                    mock_response.json.return_value = {"Message": "receipt no not found"}
                    mock_api.post_matched_transaction.return_value = mock_response
                    mock_api_class.return_value = mock_api
                    self.assertRaises(
                        wasabi.ReceiptNumberNotFound,
                        wasabi.export,
                        export_data=agent_export_data,
                        retry_count=mock_retry_count,
                        session=mock_session,
                    )

                    # THEN
                    self.assertTrue(wasabi.bink_prometheus.increment_counter.called)
                    self.assertEqual(1, wasabi.bink_prometheus.increment_counter.call_count)
                    wasabi.bink_prometheus.increment_counter.assert_has_calls(expected_counter_calls)

    @mock.patch.object(export_wasabi, "export")
    def test_send_export_data_generic_exception(self, mock_export) -> None:
        """
        Test that an Exception exception raised from export() calls the expected prometheus metrics
        """

        # GIVEN
        wasabi = export_wasabi()
        mock_export.side_effect = KeyError
        agent_export_data = AgentExportData(
            outputs=[AgentExportDataOutput("export.json", {"origin_id": uuid4(), "ReceiptNo": None})],
            transactions=[],
            extra_data={},
        )
        mock_session = MagicMock()
        mock_retry_count = 1
        expected_counter_calls = [
            call(
                agent=wasabi,
                counter_name="requests_sent",
                increment_by=1,
                process_type="export",
                slug=wasabi.provider_slug,
            ),
            call(
                agent=wasabi,
                counter_name="failed_requests",
                increment_by=1,
                process_type="export",
                slug=wasabi.provider_slug,
            ),
        ]
        expected_histogram_calls = [
            call(
                agent=wasabi,
                histogram_name="request_latency",
                context_manager_stack=ANY,
                process_type="export",
                slug=wasabi.provider_slug,
            )
        ]

        # WHEN
        with mock.patch.object(wasabi, "bink_prometheus"):
            self.assertRaises(
                KeyError,
                wasabi._send_export_data,
                export_data=agent_export_data,
                retry_count=mock_retry_count,
                session=mock_session,
            )

            # THEN
            self.assertTrue(wasabi.bink_prometheus.increment_counter.called)
            self.assertEqual(2, wasabi.bink_prometheus.increment_counter.call_count)
            wasabi.bink_prometheus.increment_counter.assert_has_calls(expected_counter_calls)
            wasabi.bink_prometheus.use_histogram_context_manager.assert_has_calls(expected_histogram_calls)

    @mock.patch("app.exports.agents.bases.singular_export_agent.settings")
    @mock.patch.object(export_wasabi, "_save_export_transactions")
    @mock.patch.object(export_wasabi, "export")
    def test_send_export_data_ok(self, mock_export, mock_save_export_transactions, mock_settings) -> None:
        """
        Test that a successful call to export() calls the expected prometheus metrics
        """

        # GIVEN
        wasabi = export_wasabi()
        mock_export.return_value = {
            "provider_slug": wasabi.provider_slug,
            "transactions": [],
            "audit_data": {
                "request": {"body": {"origin_id": ANY, "ReceiptNo": None}, "timestamp": ANY},
                "response": {"body": {"Message": ANY}, "status_code": ANY, "timestamp": ANY},
            },
        }
        mock_save_export_transactions.return_value = None
        mock_settings.AUDIT_EXPORTS = False
        agent_export_data = AgentExportData(
            outputs=[AgentExportDataOutput("export.json", {"origin_id": uuid4(), "ReceiptNo": None})],
            transactions=[],
            extra_data={},
        )
        mock_session = MagicMock()
        mock_retry_count = 2
        expected_counter_calls = [
            call(
                agent=wasabi,
                counter_name="requests_sent",
                increment_by=1,
                process_type="export",
                slug=wasabi.provider_slug,
            ),
            call(
                agent=wasabi,
                counter_name="transactions",
                increment_by=1,
                process_type="export",
                slug=wasabi.provider_slug,
            ),
        ]
        expected_histogram_calls = [
            call(
                agent=wasabi,
                histogram_name="request_latency",
                context_manager_stack=ANY,
                process_type="export",
                slug=wasabi.provider_slug,
            )
        ]

        # WHEN
        with mock.patch.object(wasabi, "bink_prometheus"):
            wasabi._send_export_data(export_data=agent_export_data, retry_count=mock_retry_count, session=mock_session)

            # THEN
            self.assertTrue(wasabi.bink_prometheus.increment_counter.called)
            self.assertEqual(2, wasabi.bink_prometheus.increment_counter.call_count)
            wasabi.bink_prometheus.increment_counter.assert_has_calls(expected_counter_calls)
            wasabi.bink_prometheus.use_histogram_context_manager.assert_has_calls(expected_histogram_calls)
