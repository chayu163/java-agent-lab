import java.util.ArrayList;
import java.util.List;

public class Order {

    private final String id;
    private OrderState state;
    private final List<String> history;

    public Order(String id) {
        this.id = id;
        this.state = OrderState.CREATED;
        this.history = new ArrayList<>();
        this.history.add("CREATED");
    }

    public void pay() {
        if (state != OrderState.CREATED)
            throw new IllegalStateException("cannot pay in " + state);
        state = OrderState.PAID;
        history.add("PAID");
    }

    public void ship() {
        if (state != OrderState.PAID)
            throw new IllegalStateException("cannot ship in " + state);
        state = OrderState.SHIPPED;
        history.add("SHIPPED");
    }

    public void cancel() {
        if (state == OrderState.SHIPPED || state == OrderState.CANCELLED)
            throw new IllegalStateException("cannot cancel in " + state);
        state = OrderState.CANCELLED;
        history.add("CANCELLED");
    }

    public String getId() {
        return id;
    }

    public OrderState getState() {
        return state;
    }

    public List<String> getHistory() {
        return List.copyOf(history);
    }
}
