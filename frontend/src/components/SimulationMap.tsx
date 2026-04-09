import L from "leaflet";
import { memo, useEffect, useMemo, useState } from "react";
import { Circle, GeoJSON, MapContainer, Popup, TileLayer, useMap, useMapEvents } from "react-leaflet";
import type { MapCenterRow, MapOrderRow } from "../api/client.js";

type SimulationMapProps = {
    orderRows: MapOrderRow[];
    centerRows: MapCenterRow[];
    selectedOrderId?: string | null;
    selectedOrder?: MapOrderRow | null;
};

export const SimulationMap = memo(function SimulationMap({ orderRows, centerRows, selectedOrderId, selectedOrder }: SimulationMapProps) {
    const [zoomLevel, setZoomLevel] = useState<number>(5);
    const orderFeatures = useMemo<GeoJSON.FeatureCollection<GeoJSON.Point>>(
        () => ({
            type: "FeatureCollection",
            features: orderRows.map((row) => ({
                type: "Feature",
                geometry: {
                    type: "Point",
                    coordinates: [row.customer_lon, row.customer_lat],
                },
                properties: {
                    ...row,
                },
            })),
        }),
        [orderRows],
    );
    return (
        <div className="map-panel">
            <MapContainer center={[36.2, 138.2]} zoom={5} scrollWheelZoom preferCanvas className="leaflet-map">
                <MapZoomTracker onZoomChange={setZoomLevel} />
                <SelectedOrderViewport selectedOrder={selectedOrder} />
                <TileLayer
                    attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
                    url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                />
                <GeoJSON
                    key={`orders-${zoomLevel}-${selectedOrderId ?? "none"}`}
                    data={orderFeatures}
                    pointToLayer={(feature, latlng) => {
                        const properties = feature.properties as MapOrderRow;
                        const isSelected = properties.order_id === selectedOrderId;

                        return L.circleMarker(latlng, {
                            radius: getOrderRadius(zoomLevel, isSelected),
                            fillColor: getOrderColor(properties),
                            color: isSelected ? "#111827" : properties.is_unassigned ? "#7f1d1d" : "rgba(11, 26, 43, 0.12)",
                            weight: isSelected ? 2.4 : properties.is_unassigned ? 1.6 : 0.9,
                            opacity: 1,
                            fillOpacity: isSelected ? 1 : properties.is_unassigned ? 0.98 : 0.72,
                        });
                    }}
                    onEachFeature={(feature, layer) => {
                        const properties = feature.properties as MapOrderRow;
                        layer.bindPopup(
                            [
                                `<strong>注文ID:</strong> ${properties.order_id}`,
                                `<strong>配達拠点:</strong> ${getAssignedCenterDisplayText(properties)}`,
                                `<strong>重量:</strong> ${properties.weight_kg.toFixed(1)} kg`,
                                `<strong>配送コスト:</strong> ¥${Math.round(properties.simulated_cost).toLocaleString("ja-JP")}`,
                            ].join("<br>"),
                        );
                    }}
                />
                {centerRows.map((centerRow) => {
                    const assignedOrderCount = getCenterAssignedOrderCount(centerRow);
                    const deliveryRadiusKm = getCenterDeliveryRadiusKm(centerRow);
                    const popupContent = (
                        <>
                            <strong>拠点:</strong> {centerRow.center_name}<br />
                            <strong>担当件数:</strong> {assignedOrderCount.toLocaleString("ja-JP")} 件<br />
                            <strong>配達半径:</strong> {deliveryRadiusKm.toFixed(1)} km<br />
                            <strong>人員数:</strong> {centerRow.staffing_level.toLocaleString("ja-JP")} 人<br />
                            <strong>固定費:</strong> ¥{Math.round(centerRow.fixed_cost).toLocaleString("ja-JP")}
                        </>
                    );

                    return (
                        deliveryRadiusKm > 0 ? (
                            <Circle
                                key={`${centerRow.center_id}-range`}
                                center={[centerRow.center_lat, centerRow.center_lon]}
                                radius={deliveryRadiusKm * 1000}
                                pathOptions={{
                                    fillColor: "#ea580c",
                                    color: "#c2410c",
                                    weight: 2,
                                    opacity: 0.78,
                                    fillOpacity: 0.12,
                                }}
                            >
                                <Popup>{popupContent}</Popup>
                            </Circle>
                        ) : null
                    );
                })}
            </MapContainer>
        </div>
    );
});

function MapZoomTracker({ onZoomChange }: { onZoomChange: (zoom: number) => void }) {
    useMapEvents({
        zoomend(event) {
            onZoomChange(event.target.getZoom());
        },
    });

    return null;
}

function SelectedOrderViewport({ selectedOrder }: { selectedOrder?: MapOrderRow | null }) {
    const map = useMap();

    useEffect(() => {
        if (!selectedOrder) {
            return;
        }

        map.flyTo([selectedOrder.customer_lat, selectedOrder.customer_lon], Math.max(map.getZoom(), 9), {
            animate: true,
            duration: 0.6,
        });
    }, [map, selectedOrder]);

    return null;
}

function getOrderRadius(zoomLevel: number, isSelected: boolean): number {
    if (zoomLevel <= 5) {
        return isSelected ? 4.5 : 3;
    }

    return isSelected ? 6.5 : 5.5;
}

function getOrderColor(row: MapOrderRow): string {
    return `rgb(${row.color_r}, ${row.color_g}, ${row.color_b})`;
}

function getAssignedCenterDisplayText(row: MapOrderRow): string {
    if (row.assignment_status === "割当済" && row.assigned_center_name.trim() !== "") {
        return row.assigned_center_name;
    }

    return "未割当";
}

function getCenterAssignedOrderCount(row: MapCenterRow): number {
    const value = (row as MapCenterRow & { assigned_order_count?: number }).assigned_order_count;
    return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function getCenterDeliveryRadiusKm(row: MapCenterRow): number {
    const value = (row as MapCenterRow & { delivery_radius_km?: number }).delivery_radius_km;
    return typeof value === "number" && Number.isFinite(value) ? value : 0;
}
