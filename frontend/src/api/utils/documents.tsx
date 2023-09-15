import { backendUrl } from "~/config";
import { BackendDocumentType, type BackendDocument } from "~/types/backend/document";
import { type SecDocument } from "~/types/document";
import { documentColors } from "~/utils/colors";

export const fromBackendDocumentToFrontend = (
  backendDocuments: BackendDocument[]
) => {
  const frontendDocs: SecDocument[] = [];
  backendDocuments.map((backendDoc, index) => {
    const frontendDocType = BackendDocumentType.TenK;

    // we have 10 colors for 10 documents
    const colorIndex = index < 10 ? index : 0;
    const payload = {
      id: backendDoc,
      url: `${backendUrl}api/download/${backendDoc}`,
      ticker: backendDoc.split(".")[0],
      fullName: backendDoc.split(".")[0],
      year: '',
      docType: frontendDocType,
      color: documentColors[colorIndex],
      quarter: "",
    } as SecDocument;
    frontendDocs.push(payload);
  });
  return frontendDocs;
};
