import { useCallback, useState } from "react";
import { useDropzone } from "react-dropzone";
import './styles.css';

export default function FileUpload() {
    const [fileList, setFileList] = useState([]);

    const onDrop = useCallback(async (droppedFiles) => {
        const labelledFiles = droppedFiles.reduce((acc, file) => {
            const resultFile = file;
            resultFile.allowed = (
                file.name.toLowerCase().endsWith(".fits") || file.name.toLowerCase() === "journal.txt"
            );
            return [...acc, resultFile];
        }, []);
        setFileList(old => [...old, ...labelledFiles]);
        console.log(droppedFiles)
    }, []);

    const { getRootProps, getInputProps, isDragActive } = useDropzone({
        onDrop
    });

    const onUpload = async () => {
        const formData = new FormData();
        fileList.forEach(file => {
            if (file.allowed) {
                formData.append("files", file);
            }
        });
        console.log(formData)

        const response = await fetch("/api/upload", {
            method: "POST",
            body: formData
        });

        const result = await response.json();
        console.log(result);
    }

    return (
        <div className="drop-file-preview">
            <div
                {...getRootProps()}
                style={{
                border: "2px dashed #888",
                padding: "40px",
                textAlign: "center",
                cursor: "pointer"
                }}
            >
                <input {...getInputProps()} />

                {isDragActive
                ? "Drop the file here..."
                : "Drag & drop a file here, or click to select"}

            </div>
            <div className="drop-file-preview">
                {
                    fileList.map(file => {
                        return <div key={file.index} className="drop-file-preview__item">
                            <div>{ file.name }</div>
                            <div>{
                                file.allowed ? 'OK' : 'X'
                            }</div>
                        </div>
                    })
                }
            </div>
            <div>
                <button onClick={onUpload}>
                    Upload
                </button>
            </div>
        </div>
    );
}
