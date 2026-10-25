from app.utils.bank_csv import parse_easybank_csv


def test_kontotransfer_is_imported_as_transfer():
    content = (
        "1;Kontotransfer;25.10.2026;unused;-25,00;EUR\n"
    ).encode("utf-8")

    entries, errors, transfer_count = parse_easybank_csv(content)

    assert errors == []
    assert transfer_count == 1
    assert len(entries) == 1
    assert entries[0].entry_type == "transfer"
    assert entries[0].category == "Transfer"
